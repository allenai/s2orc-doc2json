import os
import unittest
import json

from doc2json.s2orc import load_s2orc

TEST_S2ORC_INPUT_DATA = os.path.join('tests', 's2orc')
TEST_S2ORC_CURRENT = os.path.join(TEST_S2ORC_INPUT_DATA, '20210101')
TEST_S2ORC_2020_DATA = os.path.join(TEST_S2ORC_INPUT_DATA, '20200705')
TEST_S2ORC_2019_DATA = os.path.join(TEST_S2ORC_INPUT_DATA, '20190928')


class TestS2ORC(unittest.TestCase):

    def test_s2orc_current(self):
        """
        Check loading current s2orc files
        :return:
        """
        for fname in os.listdir(TEST_S2ORC_CURRENT):
            if fname.endswith('.json'):
                print(fname)
                # get paper id
                pid = fname.split('.')[0]
                # load file
                file_path = os.path.join(TEST_S2ORC_CURRENT, fname)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                # load into s2orc class
                paper = load_s2orc(data)
                assert pid == paper.paper_id
                assert paper.metadata == {} or paper.metadata
                assert paper.abstract == [] or paper.abstract
                assert paper.body_text == [] or paper.body_text
                assert paper.bib_entries == {} or paper.bib_entries
                assert paper.ref_entries == {} or paper.ref_entries
                assert paper.as_json()
                assert paper.release_json()

    def test_s2orc_2020(self):
        """
        Check loading old s2orc from 2020/07 release
        :return:
        """
        for fname in os.listdir(TEST_S2ORC_2020_DATA):
            if fname.endswith('.json'):
                print(fname)
                # get paper id
                pid = fname.split('.')[0]
                # load file
                file_path = os.path.join(TEST_S2ORC_2020_DATA, fname)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                # load into s2orc class
                paper = load_s2orc(data)
                assert pid == paper.paper_id
                assert paper.metadata == {} or paper.metadata
                assert paper.abstract == [] or paper.abstract
                assert paper.body_text == [] or paper.body_text
                assert paper.bib_entries == {} or paper.bib_entries
                assert paper.ref_entries == {} or paper.ref_entries
                assert paper.as_json()
                assert paper.release_json()

    def test_s2orc_2019(self):
        """
        Check loading old s2orc from 2019/09 release
        :return:
        """
        for fname in os.listdir(TEST_S2ORC_2019_DATA):
            if fname.endswith('.json'):
                print(fname)
                # get paper id
                pid = fname.split('.')[0]
                # load file
                file_path = os.path.join(TEST_S2ORC_2019_DATA, fname)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                # load into s2orc class
                paper = load_s2orc(data)
                assert pid == paper.paper_id
                assert paper.metadata == {} or paper.metadata
                assert paper.abstract == [] or paper.abstract
                assert paper.body_text == [] or paper.body_text
                assert paper.bib_entries == {} or paper.bib_entries
                assert paper.ref_entries == {} or paper.ref_entries
                assert paper.as_json()
                assert paper.release_json()