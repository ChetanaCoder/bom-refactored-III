import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import re

def parse_repomix_xml_and_create_zip(xml_content, output_zip_path):
    """
    Parse a Repomix XML file and create a zip file with the proper directory structure
    """
    
    # Create a temporary directory to store extracted files
    temp_dir = Path("temp_project_extraction")
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Parse the XML content to extract individual files
        files_extracted = extract_files_from_repomix(xml_content, temp_dir)
        
        # Create the zip file
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_info in files_extracted:
                file_path = file_info['path']
                full_path = temp_dir / file_path
                
                if full_path.exists():
                    # Add file to zip with proper path
                    zipf.write(full_path, file_path)
                    print(f"Added to zip: {file_path}")
        
        print(f"\\nZip file created successfully: {output_zip_path}")
        print(f"Total files added: {len(files_extracted)}")
        
    finally:
        # Clean up temporary directory
        cleanup_temp_dir(temp_dir)

def extract_files_from_repomix(xml_content, output_dir):
    """
    Extract files from Repomix XML format
    """
    files_extracted = []
    
    # Find all file sections using regex
    file_pattern = r'<file path="([^"]+)">(.*?)</file>'
    matches = re.findall(file_pattern, xml_content, re.DOTALL)
    
    for file_path, file_content in matches:
        # Skip .Zone.Identifier files
        if '.Zone.Identifier' in file_path:
            continue
        
        # Create the full path
        full_path = output_dir / file_path
        
        # Create directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file content
        try:
            # Clean up the content - remove any XML escaping
            clean_content = file_content.strip()
            clean_content = clean_content.replace('&amp;', '&')
            clean_content = clean_content.replace('&lt;', '<')
            clean_content = clean_content.replace('&gt;', '>')
            clean_content = clean_content.replace('&quot;', '"')
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(clean_content)
            
            files_extracted.append({
                'path': file_path,
                'size': len(clean_content)
            })
            
            print(f"Extracted: {file_path} ({len(clean_content):,} chars)")
            
        except Exception as e:
            print(f"Error extracting {file_path}: {str(e)}")
    
    return files_extracted

def cleanup_temp_dir(temp_dir):
    """
    Clean up the temporary directory
    """
    import shutil
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary directory: {temp_dir}")

def create_project_from_xml(xml_file_path, output_zip_path="enhanced-bom-platform.zip"):
    """
    Main function to create project zip from XML file
    """
    print(f"Reading XML file: {xml_file_path}")
    
    with open(xml_file_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    print(f"XML file size: {len(xml_content):,} characters")
    
    # Extract and create zip
    parse_repomix_xml_and_create_zip(xml_content, output_zip_path)
    
    return output_zip_path

# Example usage:
# create_project_from_xml("repomix-bom-refactored.xml", "autonomous-bom-platform-enhanced.zip")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python xml_to_zip.py <xml_file_path> [output_zip_path]")
        sys.exit(1)
    
    xml_file = sys.argv[1]
    output_zip = sys.argv[2] if len(sys.argv) > 2 else "enhanced-bom-platform.zip"
    
    if not os.path.exists(xml_file):
        print(f"Error: XML file '{xml_file}' not found")
        sys.exit(1)
    
    try:
        result_zip = create_project_from_xml(xml_file, output_zip)
        print(f"\\n✅ Successfully created: {result_zip}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)