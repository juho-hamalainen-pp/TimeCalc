import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from collections import defaultdict


class EstTimeCalculatorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EstTime Calculator - XML Element Selector")
        self.root.geometry("900x700")
        
        self.element_data = {}  # {element_name: {'times': [values], 'var': tk.BooleanVar()}}
        self.xml_file = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Top frame for file selection
        file_frame = ttk.Frame(self.root, padding="10")
        file_frame.pack(fill=tk.X)
        
        ttk.Label(file_frame, text="XML File:").pack(side=tk.LEFT)
        
        self.file_label = ttk.Label(file_frame, text="No file selected", 
                                     foreground="gray", wraplength=500)
        self.file_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(file_frame, text="Browse...", 
                   command=self.browse_file).pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Control buttons frame
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        ttk.Button(control_frame, text="Select All", 
                   command=self.select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Deselect All", 
                   command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Calculate", 
                   command=self.calculate_sum, 
                   style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        
        # Main content frame with scrollbar
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Element checkboxes with scrollbar
        left_frame = ttk.LabelFrame(main_frame, text="Select Elements", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(left_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        self.checkbox_frame = ttk.Frame(canvas)
        
        self.checkbox_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.checkbox_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right side - Statistics display
        right_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.stats_text = tk.Text(right_frame, width=40, height=20, 
                                   font=("Consolas", 10), wrap=tk.WORD)
        stats_scroll = ttk.Scrollbar(right_frame, orient="vertical", 
                                      command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=stats_scroll.set)
        
        self.stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stats_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bottom frame for results
        result_frame = ttk.LabelFrame(self.root, text="Results", padding="10")
        result_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.result_label = ttk.Label(result_frame, text="Select a file and elements to calculate", 
                                       font=("Arial", 12, "bold"))
        self.result_label.pack()
        
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select XML File",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if filename:
            self.load_xml_file(filename)
            
    def load_xml_file(self, xml_file):
        try:
            # Parse the XML file
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            self.xml_file = xml_file
            self.file_label.config(text=os.path.basename(xml_file), foreground="black")
            
            # Clear previous data
            self.element_data.clear()
            for widget in self.checkbox_frame.winfo_children():
                widget.destroy()
            
            # Collect EstTime values by element type
            element_times = defaultdict(list)
            for elem in root.iter():
                if 'EstTime' in elem.attrib:
                    try:
                        value = float(elem.attrib['EstTime'])
                        element_times[elem.tag].append(value)
                    except ValueError:
                        pass
            
            # Sort by total time (descending)
            sorted_elements = sorted(element_times.items(), 
                                     key=lambda x: sum(x[1]), reverse=True)
            
            # Create checkboxes for each element type
            ttk.Label(self.checkbox_frame, text="Element Type", 
                      font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
            ttk.Label(self.checkbox_frame, text="Count", 
                      font=("Arial", 10, "bold")).grid(row=0, column=1, sticky=tk.E, padx=5, pady=5)
            ttk.Label(self.checkbox_frame, text="Total Time", 
                      font=("Arial", 10, "bold")).grid(row=0, column=2, sticky=tk.E, padx=5, pady=5)
            
            for idx, (elem_name, times) in enumerate(sorted_elements, start=1):
                var = tk.BooleanVar(value=True)  # Selected by default
                self.element_data[elem_name] = {'times': times, 'var': var}
                
                cb = ttk.Checkbutton(self.checkbox_frame, text=elem_name, 
                                     variable=var, command=self.update_preview)
                cb.grid(row=idx, column=0, sticky=tk.W, padx=5, pady=2)
                
                count_label = ttk.Label(self.checkbox_frame, text=str(len(times)))
                count_label.grid(row=idx, column=1, sticky=tk.E, padx=5, pady=2)
                
                total_label = ttk.Label(self.checkbox_frame, text=f"{sum(times):.3f}")
                total_label.grid(row=idx, column=2, sticky=tk.E, padx=5, pady=2)
            
            self.update_preview()
            messagebox.showinfo("Success", 
                                f"Loaded {len(sorted_elements)} element types from {os.path.basename(xml_file)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load XML file:\n{str(e)}")
            
    def select_all(self):
        for data in self.element_data.values():
            data['var'].set(True)
        self.update_preview()
        
    def deselect_all(self):
        for data in self.element_data.values():
            data['var'].set(False)
        self.update_preview()
        
    def update_preview(self):
        """Update the statistics display based on current selection"""
        if not self.element_data:
            return
            
        selected_elements = []
        for elem_name, data in self.element_data.items():
            if data['var'].get():
                times = data['times']
                selected_elements.append({
                    'name': elem_name,
                    'count': len(times),
                    'total': sum(times),
                    'avg': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times)
                })
        
        # Sort by total time
        selected_elements.sort(key=lambda x: x['total'], reverse=True)
        
        # Update text display
        self.stats_text.delete(1.0, tk.END)
        
        if not selected_elements:
            self.stats_text.insert(tk.END, "No elements selected")
            return
        
        # Header
        header = f"{'Element':<20} {'Count':>6} {'Total':>10} {'Avg':>10}\n"
        self.stats_text.insert(tk.END, header)
        self.stats_text.insert(tk.END, "-" * 50 + "\n")
        
        # Data rows
        total_count = 0
        total_time = 0.0
        
        for elem in selected_elements:
            line = f"{elem['name']:<20} {elem['count']:>6} {elem['total']:>10.3f} {elem['avg']:>10.3f}\n"
            self.stats_text.insert(tk.END, line)
            total_count += elem['count']
            total_time += elem['total']
        
        # Footer
        self.stats_text.insert(tk.END, "-" * 50 + "\n")
        footer = f"{'TOTAL':<20} {total_count:>6} {total_time:>10.3f}\n"
        self.stats_text.insert(tk.END, footer, "bold")
        
        # Configure tag for bold text
        self.stats_text.tag_configure("bold", font=("Consolas", 10, "bold"))
        
    def calculate_sum(self):
        """Calculate and display the sum of selected elements"""
        if not self.element_data:
            messagebox.showwarning("No Data", "Please load an XML file first")
            return
        
        selected_elements = []
        total_count = 0
        total_time = 0.0
        
        for elem_name, data in self.element_data.items():
            if data['var'].get():
                times = data['times']
                selected_elements.append(elem_name)
                total_count += len(times)
                total_time += sum(times)
        
        if not selected_elements:
            messagebox.showwarning("No Selection", "Please select at least one element type")
            return
        
        # Update result display
        minutes = int(total_time // 60)
        seconds = total_time % 60
        
        result_text = (f"Selected: {len(selected_elements)} element types | "
                      f"Operations: {total_count} | "
                      f"Total Time: {total_time:.3f}s ({minutes}m {seconds:.1f}s)")
        
        self.result_label.config(text=result_text, foreground="green")
        
        # Show detailed message box
        detail_msg = f"Total EstTime: {total_time:.3f} seconds\n"
        detail_msg += f"Time: {minutes} minutes {seconds:.1f} seconds\n\n"
        detail_msg += f"Selected Elements ({len(selected_elements)}):\n"
        detail_msg += ", ".join(selected_elements)
        
        messagebox.showinfo("Calculation Complete", detail_msg)


def main():
    root = tk.Tk()
    app = EstTimeCalculatorUI(root)
    
    # Load file from command line if provided
    import sys
    if len(sys.argv) > 1:
        root.after(100, lambda: app.load_xml_file(sys.argv[1]))
    
    root.mainloop()


if __name__ == "__main__":
    main()
