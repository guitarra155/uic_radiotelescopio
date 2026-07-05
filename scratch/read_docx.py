import zipfile
import xml.etree.ElementTree as ET
import sys
import os

def read_docx(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    try:
        with zipfile.ZipFile(file_path) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            
            # Namespace for wordprocessingML
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            paragraphs = []
            for para in root.iter(f'{{{ns["w"]}}}p'):
                texts = [node.text for node in para.iter(f'{{{ns["w"]}}}t') if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            
            print(f"=== {os.path.basename(file_path)} ===")
            # Print first 150 paragraphs to get the outline
            for i, p in enumerate(paragraphs[:150]):
                print(f"{i+1}: {p}")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

if __name__ == "__main__":
    read_docx(r"c:\uic_radiotelescopio\docs\ANEXO 2 FORMATO PERFIL GUITARRA JHON v2.1.docx")
    print("\n" + "="*50 + "\n")
    read_docx(r"c:\uic_radiotelescopio\docs\Pre6_Introduccion_Tesis_UIC_Radiotelescopio - copia.docx")
