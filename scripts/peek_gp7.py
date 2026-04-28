import zipfile
import sys
import xml.etree.ElementTree as ET

path = sys.argv[1]

with zipfile.ZipFile(path) as z:
    root = ET.fromstring(z.read('Content/score.gpif').decode('utf-8'))

print("=== First Track element ===")
track = root.find('.//Tracks/Track')
print(ET.tostring(track, encoding='unicode')[:2000])

print()
print("=== First 3 MasterBar elements ===")
for i, mb in enumerate(root.findall('.//MasterBars/MasterBar')):
    if i >= 3:
        break
    print(ET.tostring(mb, encoding='unicode'))
    print()

print("=== First Bar element ===")
bar = root.find('.//Bars/Bar')
print(ET.tostring(bar, encoding='unicode'))

print()
print("=== First Voice element ===")
voice = root.find('.//Voices/Voice')
print(ET.tostring(voice, encoding='unicode'))
