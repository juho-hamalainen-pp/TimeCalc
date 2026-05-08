import xml.etree.ElementTree as ET
import os


def read_xml_file(file_path):
    """
    Read and parse an XML file.
    
    Args:
        file_path: Path to the XML file
        
    Returns:
        ElementTree root element
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found.")
            return None
        
        # Parse the XML file
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        print(f"Successfully loaded XML file: {file_path}")
        print(f"Root tag: {root.tag}")
        
        return root
    
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None


def display_xml_structure(element, level=0):
    """
    Display the structure of the XML tree.
    
    Args:
        element: XML element to display
        level: Current indentation level
    """
    indent = "  " * level
    
    # Print element tag and attributes
    attrs = " ".join([f'{k}="{v}"' for k, v in element.attrib.items()])
    if attrs:
        print(f"{indent}<{element.tag} {attrs}>")
    else:
        print(f"{indent}<{element.tag}>")
    
    # Print text content if present
    if element.text and element.text.strip():
        print(f"{indent}  {element.text.strip()}")
    
    # Recursively display children
    for child in element:
        display_xml_structure(child, level + 1)


def get_element_value(root, tag_name):
    """
    Find and return the value of a specific XML tag.
    
    Args:
        root: XML root element
        tag_name: Name of the tag to find
        
    Returns:
        Text content of the tag, or None if not found
    """
    element = root.find(f".//{tag_name}")
    if element is not None:
        return element.text
    return None


def get_all_elements(root, tag_name):
    """
    Find all elements with a specific tag name.
    
    Args:
        root: XML root element
        tag_name: Name of the tag to find
        
    Returns:
        List of matching elements
    """
    return root.findall(f".//{tag_name}")


# Example usage
if __name__ == "__main__":
    # Example: Load an XML file
    xml_file = input("Enter the path to your XML file: ")
    
    root = read_xml_file(xml_file)
    
    if root is not None:
        print("\n--- XML Structure ---")
        display_xml_structure(root)
        
        print("\n--- Available Operations ---")
        print("1. Search for a specific tag")
        print("2. Get all elements with a tag name")
        print("3. View raw XML")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "1":
            tag = input("Enter tag name to search: ")
            value = get_element_value(root, tag)
            if value:
                print(f"\n{tag}: {value}")
            else:
                print(f"\nTag '{tag}' not found")
        
        elif choice == "2":
            tag = input("Enter tag name to find all: ")
            elements = get_all_elements(root, tag)
            print(f"\nFound {len(elements)} elements:")
            for elem in elements:
                print(f"  - {elem.text if elem.text else '(no text)'}")
        
        elif choice == "3":
            print("\n--- Raw XML ---")
            print(ET.tostring(root, encoding='unicode'))
