import xml.etree.ElementTree as ET
import re

def extract_xml_from_markdown(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'<\?xml.*', content, re.DOTALL)
    if match:
        return match.group(0)
    return content

def list_layers_from_xml(xml_content):
    root = ET.fromstring(xml_content)
    layers = []
    for elem in root.iter():
        tag_local = elem.tag.split('}')[-1]
        if tag_local == 'FeatureType':
            name_elem = None
            for child in elem:
                if child.tag.split('}')[-1] == 'Name':
                    name_elem = child
                    break
            if name_elem is not None:
                title_elem = None
                for child in elem:
                    if child.tag.split('}')[-1] == 'Title':
                        title_elem = child
                        break
                title = title_elem.text if title_elem is not None else ""
                layers.append((name_elem.text, title))
    return layers

xml_sisema = extract_xml_from_markdown("/home/diegocamargo/.gemini/antigravity-cli/brain/d8e23fa5-c72a-4485-973f-9997a2d8ed2a/.system_generated/steps/114/content.md")
sisema_layers = list_layers_from_xml(xml_sisema)

xml_cprm = extract_xml_from_markdown("/home/diegocamargo/.gemini/antigravity-cli/brain/d8e23fa5-c72a-4485-973f-9997a2d8ed2a/.system_generated/steps/105/content.md")
cprm_layers = list_layers_from_xml(xml_cprm)

output = []
output.append("=== MATCHING LEYERS IN SISEMA ===")
for name, title in sisema_layers:
    name_l = name.lower()
    title_l = title.lower()
    # Procurar por termos relacionados a transporte, rodovias, ferrovias, aerodromos
    if any(k in name_l or k in title_l for k in ['rodov', 'der', 'via', 'transp', 'ferro', 'aero']):
        output.append(f"{name} | {title}")

output.append("\n=== MATCHING LAYERS IN CPRM ===")
for name, title in cprm_layers:
    name_l = name.lower()
    title_l = title.lower()
    if any(k in name_l or k in title_l for k in ['bacia', 'hidro', 'dren', 'agua', 'rio']):
        output.append(f"{name} | {title}")

with open("scratch/matching_layers.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))
print("Done writing matching layers.")
