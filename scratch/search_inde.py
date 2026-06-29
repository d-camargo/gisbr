import urllib.request
import xml.etree.ElementTree as ET
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://geoservicos.inde.gov.br/geoserver/ows?service=WFS&version=1.1.0&request=GetCapabilities"
print(f"Fetching INDE GetCapabilities from: {url}")
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        content = r.read()
    root = ET.fromstring(content)
    
    matches = []
    for elem in root.iter():
        tag_local = elem.tag.split('}')[-1]
        if tag_local == 'FeatureType':
            name_elem = None
            for child in elem:
                if child.tag.split('}')[-1] == 'Name':
                    name_elem = child
                    break
            if name_elem is not None:
                name = name_elem.text
                name_l = name.lower()
                if 'concess' in name_l or 'rodov' in name_l:
                    title_elem = None
                    for child in elem:
                        if child.tag.split('}')[-1] == 'Title':
                            title_elem = child
                            break
                    title = title_elem.text if title_elem is not None else ""
                    matches.append((name, title))
                    
    print(f"Found {len(matches)} matching layers:")
    for name, title in matches:
        print(f"  {name} | {title}")
except Exception as e:
    print(f"Error: {e}")
