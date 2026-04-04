import subprocess
res = subprocess.run(['gsutil.cmd', 'ls', 'gs://mapbiomas-fire/sudamerica/peru/monitor/library_images/monthly/chunks/2024/12/*.tif'], capture_output=True, text=True)
print('RC:', res.returncode)
print('STDOUT:', res.stdout[:100])
print('STDERR:', res.stderr[:100])
