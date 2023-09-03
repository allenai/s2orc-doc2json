#!/usr/bin/python
import setuptools
import os

requirements = [l.strip() for l in open('requirements.txt').readlines()]
if 'GITHUB_ACCESS_TOKEN' in os.environ:
    requirements.append(f"annotation_store @ git+https://{os.getenv('GITHUB_ACCESS_TOKEN')}@github.com/allenai/annotation-store@main#egg=pkg&subdirectory=clients/python")

setuptools.setup(
    name='doc2json',
    version='0.1',
    packages=setuptools.find_packages(),
    install_requires=requirements,
    tests_require=[],
    zip_safe=False,
    test_suite='py.test',
    entry_points='',
)