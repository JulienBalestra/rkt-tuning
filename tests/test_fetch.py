import json
import multiprocessing
import shutil
import statistics
import subprocess
import time
import unittest

import os
import requests

RESULTS = []


class Result:
    def __init__(self, test: str, result: list):
        self.__name__ = test
        self.result = result

        self.maximum = max(result)
        self.minimum = min(result)
        self.total = sum(result)
        self.average = self.total / len(result)
        self.median = statistics.median(result)
        self.deviation = statistics.stdev(result)


class TestFetch(unittest.TestCase):
    test_d = os.path.dirname(os.path.abspath(__file__))
    project_d = os.path.dirname(test_d)
    var_lib_rkt = os.path.join(test_d, "var-lib-rkt")

    dir_flag = "--dir=%s" % var_lib_rkt

    # upstream rkt
    rkt_official = "/usr/bin/rkt"

    # patched rkt
    rkt_patched = os.getenv("RKT_PATCHED")

    # Maybe use the pull-policy to new and avoid gci
    fetch_cmd = [dir_flag, "fetch", "--insecure-options=all", ]
    copies = []
    fetchs = []

    dev_null = open("/dev/null")

    result_url = os.getenv("RESULT_URL")

    @classmethod
    def setUpClass(cls):
        subprocess.call(["umount", cls.var_lib_rkt], stderr=cls.dev_null)
        for f in [cls.rkt_official, cls.rkt_patched]:
            assert os.path.isfile(f) is True

        for d in [cls.var_lib_rkt]:
            assert os.path.isdir(d) is True

        for i, aci in enumerate(os.getenv("ACIS", "").split(",")):
            assert subprocess.call([cls.rkt_official] + cls.fetch_cmd + [aci]) == 0
            fs_aci = os.path.join(cls.test_d, "acis", "%d.aci" % i)
            tmpfs_aci = os.path.join(cls.var_lib_rkt, "%d.aci" % i)
            assert subprocess.call(
                [cls.rkt_official, "i", "export", "--overwrite", aci,
                 fs_aci]) == 0
            cls.copies.append((fs_aci, tmpfs_aci))
            cls.fetchs.append(cls.fetch_cmd + [tmpfs_aci])

    @classmethod
    def tearDownClass(cls):
        subprocess.call(["umount", cls.var_lib_rkt], stderr=cls.dev_null)
        cls.dev_null.close()
        print("\nSummary:")
        RESULTS.sort(key=lambda x: x.total)
        results_to_send = []
        for i, r in enumerate(RESULTS):
            print(
                "%d%% -> %s" % (
                    ((RESULTS[0].total * 100) / RESULTS[i].total), RESULTS[i].__name__)
            )
            results_to_send.append(
                r.__dict__
            )
        data = json.dumps(
            results_to_send
        )
        if cls.result_url:
            req = requests.post(cls.result_url, data, headers={'Content-Type': 'application/json'})
            req.close()
            print(
                "\n",
                cls.result_url,
                ": ",
                req.status_code
            )

    def gc(self):
        subprocess.call([self.rkt_official, self.dir_flag, "gc", "--grace-period=0s"],
                        stdout=self.dev_null, stderr=self.dev_null)

    def gci(self):
        subprocess.call([self.rkt_official, self.dir_flag, "i", "gc", "--grace-period=0s"],
                        stdout=self.dev_null, stderr=self.dev_null)

    def setUp(self):
        self.assertEqual(0, subprocess.call(["mount", "-t", "tmpfs", "-o", "size=20G", "tmpfs", self.var_lib_rkt]))
        for fs, tmpfs in self.copies:
            shutil.copy2(fs, tmpfs)
        self.gc()
        self.gci()

    def tearDown(self):
        self.gc()
        self.gci()
        self.assertEqual(0, subprocess.call(["umount", self.var_lib_rkt], stderr=self.dev_null))

    def fetch(self, test_name: str, rkt: str, gomaxprocs=1, iterations=10):
        result = []
        cmds = [[rkt] + k for k in self.fetchs]
        env = {"GOMAXPROCS": "%d" % gomaxprocs}
        for c in cmds:
            print(c)
        for i in range(iterations):
            before = time.time()
            for c in cmds:
                subprocess.call(
                    c,
                    env=env,
                    stdout=self.dev_null,
                )
            result.append(time.time() - before)
            self.gci()
        testing_result = Result(test_name, result)
        RESULTS.append(testing_result)
        print(
            "\n",
            self.fetch.__name__, test_name, "\n",
            "GOMAXPROCS:", gomaxprocs, "\n",
            "iterations:", iterations, "\n",
            "total:     ", testing_result.total, "\n",
            "minimum:   ", testing_result.minimum, "\n",
            "maximum:   ", testing_result.maximum, "\n",
            "average:   ", testing_result.average, "\n",
            "median:    ", testing_result.median, "\n",
            "deviation: ", testing_result.deviation, "\n",
            end="\n")

    def test_patch_gomaxprocs_1(self):
        self.fetch(self.test_patch_gomaxprocs_1.__name__, self.rkt_patched)

    def test_patch_gomaxprocs_max(self):
        self.fetch(self.test_patch_gomaxprocs_max.__name__, self.rkt_patched, gomaxprocs=multiprocessing.cpu_count())

    def test_official(self):
        self.fetch(self.test_official.__name__, self.rkt_official)


if __name__ == '__main__':
    unittest.main()
