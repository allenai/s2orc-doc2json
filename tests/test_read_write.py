import os
import unittest
import json

from doc2json.s2orc import load_s2orc

JSON_INPUT_DATA = os.path.join('tests', 'pdf', 'N18-3011.json')


class TestS2ORC(unittest.TestCase):

    def test_read_write(self):
        """
        Check loading current s2orc files
        :return:
        """
        with open(JSON_INPUT_DATA, 'r') as f:
            data = json.load(f)
        try1 = load_s2orc(data)
        output1 = try1.release_json("pdf")
        try2 = load_s2orc(data)
        output2 = try2.release_json("pdf")
        for key, value in output2.items():
            if key == 'header':
                assert value != output1[key]
            else:
                assert value == output1[key]
