import xml.etree.ElementTree as ET
import sys

def inspect_xml_file(xml_file):
    """Inspect XML file structure for Sheet elements"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        print(f"\n{'='*80}")
        print(f"XML File Inspection: {xml_file}")
        print(f"{'='*80}\n")
        
        # Check root element
        print(f"Root element: <{root.tag}>")
        if root.get("Name"):
            print(f"  Name attribute: {root.get('Name')}")
        print()
        
        # Check for Sheets container
        sheets_container = root.find("Sheets")
        if sheets_container is None:
            print("❌ No <Sheets> container found!")
            return
        
        print(f"✓ Found <Sheets> container")
        
        # Find all Sheet elements
        sheet_elements = sheets_container.findall("Sheet")
        print(f"✓ Found {len(sheet_elements)} Sheet element(s)\n")
        
        if len(sheet_elements) == 0:
            print("❌ No <Sheet> elements found inside <Sheets>!")
            print("\nShowing structure of <Sheets> element:")
            print(f"  Tag: {sheets_container.tag}")
            print(f"  Attributes: {sheets_container.attrib}")
            print(f"  Text: {sheets_container.text}")
            print(f"  Children:")
            for child in sheets_container:
                print(f"    <{child.tag}> with {len(list(child))} children")
            return
        
        # Inspect each Sheet
        for i, sheet_elem in enumerate(sheet_elements, 1):
            print(f"\nSheet #{i}:")
            print(f"  Tag: <{sheet_elem.tag}>")
            
            # Check attributes
            if sheet_elem.attrib:
                print(f"  Attributes: {sheet_elem.attrib}")
            else:
                print(f"  Attributes: (none)")
            
            # Check for StartTime
            start_time = sheet_elem.find("StartTime")
            if start_time is not None:
                print(f"  StartTime: {start_time.text}")
            else:
                print(f"  StartTime: (not found)")
            
            # Check for EndTime
            end_time = sheet_elem.find("EndTime")
            if end_time is not None:
                print(f"  EndTime: {end_time.text}")
            else:
                print(f"  EndTime: (not found)")
            
            # Check for Times container
            times_elem = sheet_elem.find("Times")
            if times_elem is not None:
                time_elements = times_elem.findall("Time")
                print(f"  Times: Found {len(time_elements)} Time element(s)")
                
                # Show first few Time elements as samples
                for j, time_elem in enumerate(time_elements[:3], 1):
                    command = time_elem.get("Command", "(no Command attr)")
                    value = time_elem.text if time_elem.text else "(no text)"
                    print(f"    Time #{j}: Command='{command}', Value='{value}'")
                
                if len(time_elements) > 3:
                    print(f"    ... and {len(time_elements) - 3} more Time elements")
            else:
                print(f"  Times: (not found)")
            
            # List all direct children
            children = list(sheet_elem)
            print(f"  Total child elements: {len(children)}")
            child_tags = [child.tag for child in children]
            print(f"  Child tags: {', '.join(child_tags)}")
        
        print(f"\n{'='*80}")
        print("Inspection complete!")
        print(f"{'='*80}\n")
        
    except ET.ParseError as e:
        print(f"❌ XML Parse Error: {e}")
    except FileNotFoundError:
        print(f"❌ File not found: {xml_file}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_xml_sheets.py <xml_file>")
        print("\nThis tool inspects XML files to diagnose why Sheet elements may not be detected.")
        sys.exit(1)
    
    inspect_xml_file(sys.argv[1])
