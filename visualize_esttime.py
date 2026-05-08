import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import os
from collections import defaultdict


def analyze_esttime_by_element(xml_file):
    """
    Analyze EstTime values grouped by XML element type.
    
    Args:
        xml_file: Path to the XML file
        
    Returns:
        Dictionary with element names as keys and lists of EstTime values
    """
    try:
        # Check if file exists
        if not os.path.exists(xml_file):
            print(f"Error: File '{xml_file}' not found.")
            return None
        
        # Parse the XML file
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Group EstTime values by element tag
        element_times = defaultdict(list)
        
        # Iterate through all elements in the tree
        for elem in root.iter():
            if 'EstTime' in elem.attrib:
                try:
                    value = float(elem.attrib['EstTime'])
                    element_times[elem.tag].append(value)
                except ValueError:
                    print(f"Warning: Could not convert EstTime value '{elem.attrib['EstTime']}' to float")
        
        return dict(element_times)
    
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None


def create_visualizations(element_times, xml_file):
    """
    Create multiple visualizations for EstTime data.
    
    Args:
        element_times: Dictionary with element names and their EstTime values
        xml_file: Name of the XML file for the title
    """
    if not element_times:
        print("No data to visualize")
        return
    
    # Calculate statistics for each element type
    element_stats = {}
    for elem_name, times in element_times.items():
        element_stats[elem_name] = {
            'total': sum(times),
            'count': len(times),
            'average': sum(times) / len(times),
            'min': min(times),
            'max': max(times)
        }
    
    # Sort by total time (descending)
    sorted_elements = sorted(element_stats.items(), key=lambda x: x[1]['total'], reverse=True)
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(f'EstTime Analysis - {os.path.basename(xml_file)}', fontsize=16, fontweight='bold')
    
    # 1. Bar chart - Total EstTime by Element Type
    ax1 = plt.subplot(2, 2, 1)
    elements = [item[0] for item in sorted_elements]
    totals = [item[1]['total'] for item in sorted_elements]
    colors = plt.cm.viridis([i/len(elements) for i in range(len(elements))])
    
    bars1 = ax1.barh(elements, totals, color=colors)
    ax1.set_xlabel('Total EstTime (seconds)', fontweight='bold')
    ax1.set_title('Total EstTime by Element Type', fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)
    
    # Add value labels on bars
    for i, (bar, total) in enumerate(zip(bars1, totals)):
        ax1.text(total, bar.get_y() + bar.get_height()/2, f'{total:.1f}', 
                va='center', ha='left', fontsize=8, fontweight='bold')
    
    # 2. Bar chart - Count of Operations by Element Type
    ax2 = plt.subplot(2, 2, 2)
    counts = [item[1]['count'] for item in sorted_elements]
    
    bars2 = ax2.barh(elements, counts, color=colors)
    ax2.set_xlabel('Number of Operations', fontweight='bold')
    ax2.set_title('Operation Count by Element Type', fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)
    
    # Add value labels on bars
    for bar, count in zip(bars2, counts):
        ax2.text(count, bar.get_y() + bar.get_height()/2, f'{count}', 
                va='center', ha='left', fontsize=8, fontweight='bold')
    
    # 3. Bar chart - Average EstTime by Element Type
    ax3 = plt.subplot(2, 2, 3)
    averages = [item[1]['average'] for item in sorted_elements]
    
    bars3 = ax3.barh(elements, averages, color=colors)
    ax3.set_xlabel('Average EstTime (seconds)', fontweight='bold')
    ax3.set_title('Average EstTime by Element Type', fontweight='bold')
    ax3.grid(axis='x', alpha=0.3)
    
    # Add value labels on bars
    for bar, avg in zip(bars3, averages):
        ax3.text(avg, bar.get_y() + bar.get_height()/2, f'{avg:.3f}', 
                va='center', ha='left', fontsize=8, fontweight='bold')
    
    # 4. Pie chart - Percentage of Total Time by Element Type
    ax4 = plt.subplot(2, 2, 4)
    
    # Show only top elements for clarity, group others
    top_n = 10
    if len(sorted_elements) > top_n:
        top_elements = sorted_elements[:top_n]
        other_total = sum(item[1]['total'] for item in sorted_elements[top_n:])
        pie_labels = [item[0] for item in top_elements] + ['Others']
        pie_values = [item[1]['total'] for item in top_elements] + [other_total]
    else:
        pie_labels = [item[0] for item in sorted_elements]
        pie_values = [item[1]['total'] for item in sorted_elements]
    
    wedges, texts, autotexts = ax4.pie(pie_values, labels=pie_labels, autopct='%1.1f%%',
                                         startangle=90, colors=colors)
    ax4.set_title('Time Distribution by Element Type', fontweight='bold')
    
    # Improve text readability
    for text in texts:
        text.set_fontsize(8)
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(8)
    
    plt.tight_layout()
    
    # Print summary statistics BEFORE showing the plot
    print("\n" + "="*80)
    print(f"SUMMARY STATISTICS - {os.path.basename(xml_file)}")
    print("="*80)
    print(f"{'Element Type':<25} {'Count':>8} {'Total':>12} {'Average':>12} {'Min':>10} {'Max':>10}")
    print("-"*80)
    
    for elem_name, stats in sorted_elements:
        print(f"{elem_name:<25} {stats['count']:>8} {stats['total']:>12.3f} "
              f"{stats['average']:>12.3f} {stats['min']:>10.3f} {stats['max']:>10.3f}")
    
    print("-"*80)
    total_operations = sum(item[1]['count'] for item in sorted_elements)
    total_time = sum(item[1]['total'] for item in sorted_elements)
    print(f"{'TOTAL':<25} {total_operations:>8} {total_time:>12.3f}")
    print("="*80)
    
    # Save the figure
    output_file = os.path.splitext(xml_file)[0] + '_esttime_analysis.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nGraph saved to: {output_file}")
    plt.close()  # Close the figure to free memory


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
    else:
        xml_file = input("Enter the path to your XML file: ")
    
    print(f"Analyzing {os.path.basename(xml_file)}...")
    element_times = analyze_esttime_by_element(xml_file)
    
    if element_times:
        create_visualizations(element_times, xml_file)
