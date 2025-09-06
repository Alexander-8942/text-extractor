import streamlit as st
import os, json, zipfile, re, xml.etree.ElementTree as ET

# --- Utility Functions ---
def roman_to_int(roman):
    roman_numerals = {'M':1000,'CM':900,'D':500,'CD':400,
                      'C':100,'XC':90,'L':50,'XL':40,
                      'X':10,'IX':9,'V':5,'IV':4,'I':1}
    i,num=0,0; roman=roman.upper()
    while i<len(roman):
        if i+1<len(roman) and roman[i:i+2] in roman_numerals:
            num+=roman_numerals[roman[i:i+2]]; i+=2
        else:
            num+=roman_numerals[roman[i]]; i+=1
    return num

def is_roman(s):
    return re.fullmatch(r"[ivxlcdmIVXLCDM]+", s) is not None

def process_idml(idml_file):
    base_name = os.path.splitext(os.path.basename(idml_file))[0].replace(" ","_")
    extract_dir = base_name
    if not os.path.exists(extract_dir):
        with zipfile.ZipFile(idml_file,'r') as zip_ref:
            zip_ref.extractall(extract_dir)

    stories_path, spreads_path = os.path.join(extract_dir,"Stories"), os.path.join(extract_dir,"Spreads")
    page_to_stories, story_texts = {}, {}

    # Map pages to stories
    for fname in os.listdir(spreads_path):
        if not fname.endswith(".xml"): continue
        tree = ET.parse(os.path.join(spreads_path,fname)); root = tree.getroot()
        pages=[]
        for page in root.findall(".//Page"):
            page_name=page.get("Name")
            xform=page.get("ItemTransform").split(); x_offset=float(xform[4]) if len(xform)>4 else 0
            pages.append((page.get("Self"), page_name, x_offset))
        pages.sort(key=lambda x:x[2])

        for tf in root.findall(".//TextFrame"):
            story=tf.get("ParentStory")
            xform=tf.get("ItemTransform").split()
            x_pos=float(xform[4]) if len(xform)>4 else 0
            page_name=pages[0][1] if len(pages)==1 else (pages[0][1] if x_pos<0 else pages[1][1])
            page_to_stories.setdefault(page_name, []).append(story)

    # Extract text from stories
    for fname in os.listdir(stories_path):
        if not fname.endswith(".xml"): continue
        tree = ET.parse(os.path.join(stories_path,fname)); root = tree.getroot()
        sid = root.find(".//Story").get("Self")
        texts = [c.text.strip() for c in root.findall(".//Content") if c.text]
        story_texts[sid] = "\n".join(texts)

    # Combine pages
    pages=[]
    for p,stories in page_to_stories.items():
        text="\n".join(story_texts.get(s,"") for s in stories)
        if is_roman(p): pages.append((roman_to_int(p),"roman",p,text))
        else:
            try: pages.append((10000+int(p),"numeric",p,text))
            except: pass
    pages.sort(key=lambda x:x[0])

    json_data=[{"page_number":p,"page_type":t,"content":c} for _,t,p,c in pages]
    txt_data="\n\n".join([f"<PAGE number='{p}' type='{t}'>\n{c}\n</PAGE>" for _,t,p,c in pages])
    return json_data, txt_data

# --- Streamlit UI ---
st.title("📖 IDML Text Extractor")
st.write("Upload your `.idml` file and download extracted JSON & TXT.")

uploaded = st.file_uploader("Upload IDML File", type=["idml"])
if uploaded:
    with open(uploaded.name, "wb") as f:
        f.write(uploaded.read())
    json_data, txt_data = process_idml(uploaded.name)

    st.download_button("⬇️ Download TXT", txt_data, file_name=uploaded.name.replace(".idml","_extracted.txt"))
    st.download_button("⬇️ Download JSON", json.dumps(json_data, ensure_ascii=False, indent=2),
                       file_name=uploaded.name.replace(".idml","_extracted.json"))
    st.success("✅ Extraction complete! Files ready to download.")
