import xml.etree.ElementTree as ET
import os


def sum_esttime_values(xml_file):
    """
    Sum all EstTime attribute values from an XML file.
    
    Args:
        xml_file: Path to the XML file
        
    Returns:
        Total sum of all EstTime values
    """
    try:
        # Check if file exists
        if not os.path.exists(xml_file):
            print(f"Error: File '{xml_file}' not found.")
            return None
        
        # Parse the XML file
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Find all elements with EstTime attribute
        total_sum = 0.0
        count = 0
        
        # Iterate through all elements in the tree
        for elem in root.iter():
            if 'EstTime' in elem.attrib:
                try:
                    value = float(elem.attrib['EstTime'])
                    total_sum += value
                    count += 1
                except ValueError:
                    print(f"Warning: Could not convert EstTime value '{elem.attrib['EstTime']}' to float")
        
        print(f"File: {os.path.basename(xml_file)}")
        print(f"Found {count} elements with EstTime attribute")
        print(f"Total EstTime sum: {total_sum:.3f}")
        print(f"Average EstTime: {total_sum/count:.3f}" if count > 0 else "")
        
        return total_sum
    
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None


if __name__ == "__main__":
    # Use the file from command line or ask for input
    import sys
    
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
    else:
        xml_file = input("Enter the path to your XML file: ")
    
    sum_esttime_values(xml_file)
