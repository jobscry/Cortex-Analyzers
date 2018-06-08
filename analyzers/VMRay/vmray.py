#!/usr/bin/env python
from cortexutils.analyzer import Analyzer
from vmrayclient import VMRayClient
from time import sleep


class VMRayAnalyzer(Analyzer):
    """
    VMRay analyzer that uses VMRayClient to connect to an VMRay instance. Allows uploading a sample and getting
    information via hash. More info regarding configuration in the complete documentation.
    """
    def __init__(self):
        Analyzer.__init__(self)
        self.url = self.get_param('config.url', None, 'No VMRay url given.').rstrip('/ ')
        disable_reanalyze = self.get_param('config.disablereanalyze', False)
        if disable_reanalyze == 'true' or disable_reanalyze:
            reanalyze = False
        else:
            reanalyze = True

        verify = self.get_param('config.certverify', None, 'Certificate verification parameter is missing.')
        certpath = self.get_param('config.certpath', None)
        if verify and certpath:
            verify = certpath
        self.vmrc = VMRayClient(url=self.url,
                                key=self.get_param('config.key', None, 'No VMRay API key given.'),
                                cert=verify,
                                reanalyze=reanalyze)

    def run(self):
        if self.data_type == 'hash':
            self.report({'scanreport': self.vmrc.get_sample(self.get_data())})
        elif self.data_type == 'file':
            filepath = self.get_param('file')
            filename = self.get_param('filename')
            submit_report = self.vmrc.submit_sample(filepath=filepath,
                                                    filename=filename)
            # Check for completion
            while not self.vmrc.query_job_status(submissionid=submit_report['data']['submissions'][0]['submission_id']):
                sleep(10)

            # Return the results
            self.report({'scanreport': self.vmrc.get_sample(
                samplehash=submit_report['data']['submissions'][0]['submission_sample_sha256'])
            })
        else:
            self.error('Data type currently not supported')

    def summary(self, raw):
        taxonomies = []
        namespace = "VMRay"
        predicate = "Scan"

        r = {
            'reports': []
        }

        if raw.get('scanreport', None) and len(raw.get('scanreport').get('data')) > 0:
            for scan in raw.get('scanreport').get('data'):
                r['reports'].append({
                    'score': scan.get('sample_score'),
                    'sample_severity': scan.get('sample_severity'),
                    'sample_last_reputation_severity': scan.get('sample_last_reputation_severity'),
                    'url': scan.get('sample_webif_url')
                })

        if len(r["reports"]) == 0:
            value = "\"No Scan\""
            level = "info"
            taxonomies.append(self.build_taxonomy(level, namespace, predicate, value))
        else:
            for s in r["reports"]:
                i = 1
                if s["sample_severity"] == "not_suspicious":
                    level = "safe"
                elif s["sample_severity"] == "malicious":
                    level = "malicious"
                else:
                    level = "info"

                if r["reports"] > 1:
                    value = "\"{}( from scan {})\"".format(s["score"], i)
                else:
                    value = "{}".format(s["score"])
                taxonomies.append(self.build_taxonomy(level, namespace, predicate, value))
                i += 1

        return {"taxonomies": taxonomies}


if __name__ == '__main__':
    VMRayAnalyzer().run()
