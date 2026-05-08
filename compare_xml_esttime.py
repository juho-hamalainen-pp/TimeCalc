import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from collections import defaultdict


class EstTimeComparisonUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EstTime Comparison - XML File Comparison Tool")
        self.root.geometry("1200x800")
        
        self.file1_data = {}  # {element_name: [times]}
        self.file2_data = {}  # {element_name: [times]}
        self.file1_path = None
        self.file2_path = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Top frame for file selection
        file_frame = ttk.Frame(self.root, padding="10")
        file_frame.pack(fill=tk.X)
        
        # File 1 selection
        file1_frame = ttk.LabelFrame(file_frame, text="File 1 (Base)", padding="5")
        file1_frame.pack(fill=tk.X, pady=5)
        
        self.file1_label = ttk.Label(file1_frame, text="No file selected", 
                                      foreground="gray", wraplength=800)
        self.file1_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(file1_frame, text="Browse...", 
                   command=lambda: self.browse_file(1)).pack(side=tk.RIGHT)
        
        # File 2 selection
        file2_frame = ttk.LabelFrame(file_frame, text="File 2 (Compare)", padding="5")
        file2_frame.pack(fill=tk.X, pady=5)
        
        self.file2_label = ttk.Label(file2_frame, text="No file selected", 
                                      foreground="gray", wraplength=800)
        self.file2_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(file2_frame, text="Browse...", 
                   command=lambda: self.browse_file(2)).pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Control buttons
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        ttk.Button(control_frame, text="Compare Files", 
                   command=self.compare_files,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Export Comparison", 
                   command=self.export_comparison).pack(side=tk.LEFT, padx=5)
        
        # Mode selection
        ttk.Label(control_frame, text="View:").pack(side=tk.RIGHT, padx=5)
        self.view_mode = tk.StringVar(value="all")
        ttk.Radiobutton(control_frame, text="All", variable=self.view_mode, 
                        value="all", command=self.update_comparison_view).pack(side=tk.RIGHT)
        ttk.Radiobutton(control_frame, text="Differences", variable=self.view_mode, 
                        value="diff", command=self.update_comparison_view).pack(side=tk.RIGHT)
        ttk.Radiobutton(control_frame, text="Common", variable=self.view_mode, 
                        value="common", command=self.update_comparison_view).pack(side=tk.RIGHT)
        
        # Main content - Treeview for comparison
        tree_frame = ttk.Frame(self.root, padding="10")
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview with scrollbars
        columns = ("element", "file1_count", "file1_total", "file1_avg", 
                   "file2_count", "file2_total", "file2_avg", "diff", "diff_pct")
        
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        
        # Define column headings
        self.tree.heading("element", text="Element Type")
        self.tree.heading("file1_count", text="File 1 Count")
        self.tree.heading("file1_total", text="File 1 Total")
        self.tree.heading("file1_avg", text="File 1 Avg")
        self.tree.heading("file2_count", text="File 2 Count")
        self.tree.heading("file2_total", text="File 2 Total")
        self.tree.heading("file2_avg", text="File 2 Avg")
        self.tree.heading("diff", text="Difference")
        self.tree.heading("diff_pct", text="Diff %")
        
        # Define column widths
        self.tree.column("element", width=120, anchor=tk.W)
        self.tree.column("file1_count", width=80, anchor=tk.CENTER)
        self.tree.column("file1_total", width=100, anchor=tk.E)
        self.tree.column("file1_avg", width=100, anchor=tk.E)
        self.tree.column("file2_count", width=80, anchor=tk.CENTER)
        self.tree.column("file2_total", width=100, anchor=tk.E)
        self.tree.column("file2_avg", width=100, anchor=tk.E)
        self.tree.column("diff", width=100, anchor=tk.E)
        self.tree.column("diff_pct", width=80, anchor=tk.E)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Summary frame
        summary_frame = ttk.LabelFrame(self.root, text="Summary", padding="10")
        summary_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.summary_text = tk.Text(summary_frame, height=6, font=("Consolas", 9), wrap=tk.WORD)
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        
    def browse_file(self, file_num):
        filename = filedialog.askopenfilename(
            title=f"Select XML File {file_num}",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if filename:
            self.load_xml_file(filename, file_num)
            
    def load_xml_file(self, xml_file, file_num):
        try:
            # Parse the XML file
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Collect EstTime values by element type
            element_times = defaultdict(list)
            for elem in root.iter():
                if 'EstTime' in elem.attrib:
                    try:
                        value = float(elem.attrib['EstTime'])
                        element_times[elem.tag].append(value)
                    except ValueError:
                        pass
            
            if file_num == 1:
                self.file1_data = dict(element_times)
                self.file1_path = xml_file
                self.file1_label.config(text=os.path.basename(xml_file), foreground="blue")
                messagebox.showinfo("File 1 Loaded", 
                                    f"Loaded {len(element_times)} element types")
            else:
                self.file2_data = dict(element_times)
                self.file2_path = xml_file
                self.file2_label.config(text=os.path.basename(xml_file), foreground="green")
                messagebox.showinfo("File 2 Loaded", 
                                    f"Loaded {len(element_times)} element types")
            
            # Auto-compare if both files are loaded
            if self.file1_data and self.file2_data:
                self.compare_files()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load XML file:\n{str(e)}")
            
    def compare_files(self):
        if not self.file1_data:
            messagebox.showwarning("Missing File", "Please load File 1")
            return
        if not self.file2_data:
            messagebox.showwarning("Missing File", "Please load File 2")
            return
            
        self.update_comparison_view()
        
    def update_comparison_view(self):
        if not self.file1_data or not self.file2_data:
            return
            
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get all unique element types
        all_elements = set(self.file1_data.keys()) | set(self.file2_data.keys())
        
        # Calculate statistics for each element
        comparison_data = []
        file1_total_time = 0
        file2_total_time = 0
        file1_total_ops = 0
        file2_total_ops = 0
        
        for elem in sorted(all_elements):
            file1_times = self.file1_data.get(elem, [])
            file2_times = self.file2_data.get(elem, [])
            
            file1_count = len(file1_times)
            file1_sum = sum(file1_times)
            file1_avg = file1_sum / file1_count if file1_count > 0 else 0
            
            file2_count = len(file2_times)
            file2_sum = sum(file2_times)
            file2_avg = file2_sum / file2_count if file2_count > 0 else 0
            
            diff = file2_sum - file1_sum
            diff_pct = ((file2_sum - file1_sum) / file1_sum * 100) if file1_sum > 0 else (100 if file2_sum > 0 else 0)
            
            file1_total_time += file1_sum
            file2_total_time += file2_sum
            file1_total_ops += file1_count
            file2_total_ops += file2_count
            
            # Apply filter based on view mode
            view_mode = self.view_mode.get()
            if view_mode == "common" and (file1_count == 0 or file2_count == 0):
                continue
            elif view_mode == "diff" and (file1_count == 0 or file2_count == 0 or diff == 0):
                continue
            
            comparison_data.append({
                'element': elem,
                'file1_count': file1_count,
                'file1_total': file1_sum,
                'file1_avg': file1_avg,
                'file2_count': file2_count,
                'file2_total': file2_sum,
                'file2_avg': file2_avg,
                'diff': diff,
                'diff_pct': diff_pct
            })
        
        # Sort by absolute difference (descending)
        comparison_data.sort(key=lambda x: abs(x['diff']), reverse=True)
        
        # Populate treeview
        for data in comparison_data:
            # Format values
            values = (
                data['element'],
                data['file1_count'] if data['file1_count'] > 0 else "-",
                f"{data['file1_total']:.3f}" if data['file1_total'] > 0 else "-",
                f"{data['file1_avg']:.3f}" if data['file1_avg'] > 0 else "-",
                data['file2_count'] if data['file2_count'] > 0 else "-",
                f"{data['file2_total']:.3f}" if data['file2_total'] > 0 else "-",
                f"{data['file2_avg']:.3f}" if data['file2_avg'] > 0 else "-",
                f"{data['diff']:+.3f}",
                f"{data['diff_pct']:+.1f}%"
            )
            
            # Add color tags based on difference
            if data['diff'] > 0:
                tag = "increase"
            elif data['diff'] < 0:
                tag = "decrease"
            else:
                tag = "neutral"
            
            self.tree.insert("", tk.END, values=values, tags=(tag,))
        
        # Configure tags for colors
        self.tree.tag_configure("increase", foreground="red")
        self.tree.tag_configure("decrease", foreground="green")
        self.tree.tag_configure("neutral", foreground="gray")
        
        # Update summary
        self.update_summary(file1_total_time, file2_total_time, 
                           file1_total_ops, file2_total_ops, 
                           len(self.file1_data), len(self.file2_data))
        
    def update_summary(self, file1_time, file2_time, file1_ops, file2_ops, 
                       file1_elements, file2_elements):
        self.summary_text.delete(1.0, tk.END)
        
        time_diff = file2_time - file1_time
        time_diff_pct = (time_diff / file1_time * 100) if file1_time > 0 else 0
        ops_diff = file2_ops - file1_ops
        
        summary = f"File 1: {os.path.basename(self.file1_path) if self.file1_path else 'N/A'}\n"
        summary += f"  Total Time: {file1_time:.3f}s | Operations: {file1_ops} | Element Types: {file1_elements}\n\n"
        
        summary += f"File 2: {os.path.basename(self.file2_path) if self.file2_path else 'N/A'}\n"
        summary += f"  Total Time: {file2_time:.3f}s | Operations: {file2_ops} | Element Types: {file2_elements}\n\n"
        
        summary += f"Difference: {time_diff:+.3f}s ({time_diff_pct:+.1f}%) | Operations: {ops_diff:+d}\n"
        
        if time_diff > 0:
            summary += f"File 2 is SLOWER by {abs(time_diff):.3f} seconds"
        elif time_diff < 0:
            summary += f"File 2 is FASTER by {abs(time_diff):.3f} seconds"
        else:
            summary += "Files have EQUAL total time"
        
        self.summary_text.insert(1.0, summary)
        
    def export_comparison(self):
        if not self.file1_data or not self.file2_data:
            messagebox.showwarning("No Data", "Please load and compare two files first")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Comparison",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w') as f:
                # Write header
                f.write("EstTime Comparison Report\n")
                f.write("=" * 100 + "\n\n")
                f.write(f"File 1: {self.file1_path}\n")
                f.write(f"File 2: {self.file2_path}\n\n")
                
                # Write comparison data
                if filename.endswith('.csv'):
                    # CSV format
                    f.write("Element,File1_Count,File1_Total,File1_Avg,File2_Count,File2_Total,File2_Avg,Difference,Diff_Pct\n")
                    
                    for item in self.tree.get_children():
                        values = self.tree.item(item)['values']
                        f.write(','.join(str(v) for v in values) + '\n')
                else:
                    # Text format
                    header = f"{'Element':<20} {'F1 Cnt':>8} {'F1 Total':>12} {'F1 Avg':>10} {'F2 Cnt':>8} {'F2 Total':>12} {'F2 Avg':>10} {'Diff':>12} {'Diff %':>10}\n"
                    f.write(header)
                    f.write("-" * 100 + "\n")
                    
                    for item in self.tree.get_children():
                        values = self.tree.item(item)['values']
                        line = f"{values[0]:<20} {str(values[1]):>8} {str(values[2]):>12} {str(values[3]):>10} "
                        line += f"{str(values[4]):>8} {str(values[5]):>12} {str(values[6]):>10} "
                        line += f"{str(values[7]):>12} {str(values[8]):>10}\n"
                        f.write(line)
                
            messagebox.showinfo("Export Complete", f"Comparison exported to:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export comparison:\n{str(e)}")


def main():
    root = tk.Tk()
    app = EstTimeComparisonUI(root)
    
    # Load files from command line if provided
    import sys
    if len(sys.argv) > 1:
        root.after(100, lambda: app.load_xml_file(sys.argv[1], 1))
    if len(sys.argv) > 2:
        root.after(200, lambda: app.load_xml_file(sys.argv[2], 2))
    
    root.mainloop()


if __name__ == "__main__":
    main()
