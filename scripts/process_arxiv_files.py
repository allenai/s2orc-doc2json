import os
import boto3
import tarfile
import glob
import tqdm
import shutil
import multiprocessing
from typing import Dict

from doc2json.tex2json.process_tex import process_tex_file


def untar_file(arxiv_dump_file: str, dir_for_unarchiving: str):
    """
    Untar and unzip arxiv dump file locally
    :param arxiv_dump_file:
    :param dir_for_unarchiving:
    :return:
    """
    assert os.path.exists(arxiv_dump_file)
    os.makedirs(dir_for_unarchiving, exist_ok=True)

    # untar arxiv dump locally
    with tarfile.open(arxiv_dump_file) as tar:
        for member in tar.getmembers():
            if member.isreg():  # skip if the TarInfo is not files
                member.name = os.path.basename(member.name)  # remove the path by reset it
                tar.extract(member, dir_for_unarchiving)


def upload_folder_to_s3(s3bucket, inputDir, s3Path):
    try:
        for path, subdirs, files in os.walk(inputDir):
            for file in files:
                dest_path = path.replace(inputDir,"")
                __s3file = os.path.normpath(s3Path + '/' + dest_path + '/' + file)
                __local_file = os.path.join(path, file)
                s3bucket.upload_file(__local_file, __s3file)
    except Exception as e:
        print(" ... Failed!! Quitting Upload!!")
        print(e)
        raise e


def batch_process_arxiv_latex(batch_dict: Dict):
    """
    Process one arxiv tar file
    :param batch_dict:
    :return:
    """
    obj_key = batch_dict["obj_key"]
    local_tar_file = batch_dict["local_tar_file"]
    local_input_dir = batch_dict["local_input_dir"]
    local_temp_dir = batch_dict["local_temp_dir"]
    local_output_dir = batch_dict["local_output_dir"]
    upload_bucket_name, upload_prefix_name = batch_dict["s3_upload_info"]
    log_file = batch_dict["log_file"]

    # clear log file
    open(log_file, 'w').close()

    # download tar file
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(S3_BUCKET)
    bucket.download_file(obj_key, local_tar_file)

    # create upload bucket
    upload_bucket = s3.Bucket(upload_bucket_name)

    # untar and remove tar file
    file_name = obj_key.split('/')[-1].split('.')[0]
    local_input_subdir = os.path.join(local_input_dir, file_name)
    untar_file(local_tar_file, local_input_subdir)
    os.remove(local_tar_file)

    # glob for all gz files
    gz_files = glob.glob(os.path.join(local_input_subdir, '*.gz'))
    for gz_file in tqdm.tqdm(gz_files):
        arxiv_id = list(os.path.splitext(gz_file))[0].split('/')[-1]
        try:
            output_json_file = process_tex_file(
                input_file=gz_file,
                temp_dir=local_temp_dir,
                output_dir=local_output_dir,
                log_dir=os.path.join(local_temp_dir, 'log'),
                keep_flag=True
            )
        except Exception as e:
            print('Error: ', arxiv_id)
            with open(log_file, 'a+') as log_f:
                log_f.write(f'{arxiv_id};{e}\n')
            continue

        try:
            if output_json_file:
                # upload unzipped files and json file to s3
                local_expand_dir = os.path.join(local_temp_dir, 'latex', arxiv_id)
                s3_upload_prefix = os.path.join(upload_prefix_name, arxiv_id)
                upload_folder_to_s3(upload_bucket, local_expand_dir, s3_upload_prefix)
                # upload final json
                upload_json_fname = os.path.join(s3_upload_prefix, output_json_file.split('/')[-1])
                upload_bucket.upload_file(output_json_file, upload_json_fname)
            else:
                print('failed: ', arxiv_id)
                with open(log_file, 'a+') as log_f:
                    log_f.write(f'{arxiv_id}\n')
        except Exception as e:
            print('Error: ', arxiv_id)
            with open(log_file, 'a+') as log_f:
                log_f.write(f'{arxiv_id};{e}\n')
            continue

        # cleanup
        if os.path.exists(os.path.join(local_temp_dir, 'latex', arxiv_id)):
            shutil.rmtree(os.path.join(local_temp_dir, 'latex', arxiv_id))
        if os.path.exists(os.path.join(local_temp_dir, 'norm', arxiv_id)):
            shutil.rmtree(os.path.join(local_temp_dir, 'norm', arxiv_id))
        if os.path.exists(os.path.join(local_temp_dir, 'xml', arxiv_id)):
            shutil.rmtree(os.path.join(local_temp_dir, 'xml', arxiv_id))

    # remove all temp files
    if os.path.exists(local_input_subdir):
        shutil.rmtree(local_input_subdir)


S3_BUCKET = 'ai2-s2-lucyw'
S3_PREFIX = 'arxiv/2020_12/arXiv_src_20'

S3_OUTPUT_BUCKET = 'ai2-s2-scia11y'
S3_OUTPUT_PREFIX = 'arxiv'

LOCAL_BASE_DIR = 'arxiv'
LOCAL_TAR_DIR = os.path.join(LOCAL_BASE_DIR, 'tar')
LOCAL_INPUT_DIR = os.path.join(LOCAL_BASE_DIR, 'input')
LOCAL_TEMP_DIR = os.path.join(LOCAL_BASE_DIR, 'temp')
LOCAL_OUTPUT_DIR = os.path.join(LOCAL_BASE_DIR, 'output')
LOG_DIR = 'log'

NUM_PROCESSES = multiprocessing.cpu_count() // 8

if __name__ == '__main__':
    # make directories
    os.makedirs(LOCAL_BASE_DIR, exist_ok=True)
    os.makedirs(LOCAL_TAR_DIR, exist_ok=True)
    os.makedirs(LOCAL_INPUT_DIR, exist_ok=True)
    os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)
    os.makedirs(LOCAL_OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    # s3 resources
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(S3_BUCKET)

    # filter for files to process
    objs = list(bucket.objects.filter(Prefix=S3_PREFIX))

    # create batches
    batches = [{
        "obj_key": obj.key,
        "local_tar_file": os.path.join(LOCAL_TAR_DIR, obj.key.split('/')[-1]),
        "local_input_dir": LOCAL_INPUT_DIR,
        "local_temp_dir": LOCAL_TEMP_DIR,
        "local_output_dir": LOCAL_OUTPUT_DIR,
        "s3_upload_info": (S3_OUTPUT_BUCKET, S3_OUTPUT_PREFIX),
        "log_file": os.path.join(LOG_DIR, f"{obj.key.split('/')[-1].split('.')[0]}.log")
    } for obj in objs]

    with multiprocessing.Pool(processes=NUM_PROCESSES) as p:
        p.map(batch_process_arxiv_latex, batches)

    print('done.')
