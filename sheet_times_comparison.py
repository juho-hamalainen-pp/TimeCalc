import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from collections import defaultdict
import matplotlib
matplotlib.use('TkAgg')  # Use interactive backend for displaying plots
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.patches import Patch


class ToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("Arial", 9), padx=5, pady=5)
        label.pack()
    
    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class SheetTimesComparisonUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sheet Times Analysis - Default vs Recorded EstTime")
        self.root.geometry("1400x900")
        
        self.xml_file = None
        self.default_times = {}  # {element_name: [times]} from Main (for aggregation)
        self.sheet_times = {}  # {sheet_name: {element_name: [times]}} (for aggregation)
        self.default_timeline = []  # [(command, time), ...] in sequential order
        self.sheet_timelines = {}  # {sheet_name: [(command, time), ...]} in sequential order
        self.sheet_metadata = {}  # {sheet_name: {'start': ..., 'end': ...}}
        self.all_sheets = []
        self.tooltip_window = None
        self.element_order = []  # Track order of elements as they appear in Main
        self.current_comparison_data = []  # Store current comparison data for filtering
        self.nc_program_name = None  # Store NCProgram name
        self.last_selected_index = None  # Track last selected row for Shift+click
        
        # Chart selection preferences (remember user's choices)
        self.chart_selections = {
            'chart1_comparison': True,
            'chart2_difference': True,
            'chart3_percentage': True,
            'chart4_status': True,
            'chart6_cumulative': True,
            'chart7_waterfall': True,
            'chart8_dual_timeline': True
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        # Top frame for file selection
        file_frame = ttk.Frame(self.root, padding="10")
        file_frame.pack(fill=tk.X)
        
        ttk.Label(file_frame, text="XML File:").pack(side=tk.LEFT)
        
        self.file_label = ttk.Label(file_frame, text="No file selected", 
                                     foreground="gray", wraplength=500)
        self.file_label.pack(side=tk.LEFT, padx=10)
        
        self.program_label = ttk.Label(file_frame, text="", 
                                        foreground="navy", font=("Arial", 9, "bold"))
        self.program_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(file_frame, text="Browse...", 
                   command=self.browse_file).pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Control frame
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        ttk.Label(control_frame, text="Select Sheet:").pack(side=tk.LEFT, padx=5)
        
        self.sheet_var = tk.StringVar()
        self.sheet_combo = ttk.Combobox(control_frame, textvariable=self.sheet_var, 
                                        width=40, state="readonly")
        self.sheet_combo.pack(side=tk.LEFT, padx=5)
        self.sheet_combo.bind("<<ComboboxSelected>>", lambda e: self.display_sheet_comparison())
        
        ttk.Button(control_frame, text="Show All Sheets Summary", 
                   command=self.show_all_sheets_summary).pack(side=tk.LEFT, padx=10)
        
        # Status filter frame
        filter_frame = ttk.LabelFrame(control_frame, text="Filter by Status", padding="5")
        filter_frame.pack(side=tk.LEFT, padx=10)
        
        self.filter_faster = tk.BooleanVar(value=True)
        self.filter_ontime = tk.BooleanVar(value=True)
        self.filter_slower = tk.BooleanVar(value=True)
        
        # Use tk.Checkbutton instead of ttk for color support
        faster_check = tk.Checkbutton(filter_frame, text="✓ Faster", 
                                      variable=self.filter_faster,
                                      command=self.apply_status_filter,
                                      fg="green", selectcolor="white",
                                      font=("Arial", 9))
        faster_check.pack(side=tk.LEFT, padx=3)
        
        ontime_check = tk.Checkbutton(filter_frame, text="✓ On Time", 
                                      variable=self.filter_ontime,
                                      command=self.apply_status_filter,
                                      fg="blue", selectcolor="white",
                                      font=("Arial", 9))
        ontime_check.pack(side=tk.LEFT, padx=3)
        
        slower_check = tk.Checkbutton(filter_frame, text="⚠ Slower", 
                                      variable=self.filter_slower,
                                      command=self.apply_status_filter,
                                      fg="red", selectcolor="white",
                                      font=("Arial", 9))
        slower_check.pack(side=tk.LEFT, padx=3)
        
        # OnTime tolerance setting
        tolerance_frame = ttk.LabelFrame(control_frame, text="On Time Tolerance", padding="5")
        tolerance_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(tolerance_frame, text="±").pack(side=tk.LEFT, padx=2)
        
        self.tolerance_var = tk.DoubleVar(value=5.0)
        tolerance_spin = ttk.Spinbox(tolerance_frame, from_=0.0, to=20.0, 
                                     increment=0.5, width=6,
                                     textvariable=self.tolerance_var,
                                     command=self.update_tolerance)
        tolerance_spin.pack(side=tk.LEFT, padx=2)
        tolerance_spin.bind('<Return>', lambda e: self.update_tolerance())
        tolerance_spin.bind('<FocusOut>', lambda e: self.update_tolerance())
        
        ttk.Label(tolerance_frame, text="%").pack(side=tk.LEFT, padx=2)
        
        ttk.Button(control_frame, text="Select Charts", 
                   command=self.show_chart_selection).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(control_frame, text="Visualize", 
                   command=self.create_visualization).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(control_frame, text="Export Report", 
                   command=self.export_report).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(control_frame, text="Export Multiple Sheets", 
                   command=self.export_multiple_sheets).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(control_frame, text="Column Visibility", 
                   command=self.show_column_settings).pack(side=tk.RIGHT, padx=5)
        
        # Add selection count label
        self.selection_label = ttk.Label(control_frame, text="Selected: 0/0", 
                                         foreground="blue")
        self.selection_label.pack(side=tk.LEFT, padx=10)
        
        # Main content - PanedWindow for resizable sections
        paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top section - Comparison table
        tree_frame = ttk.LabelFrame(paned, text="Timeline Comparison (Row by Row)", padding="10")
        paned.add(tree_frame, weight=3)
        
        # Create treeview - timeline comparison
        columns = ("selected", "row", "element", "feedrate", "sorting_address", "comment",
                   "default_total", "recorded_total",
                   "default_avg", "recorded_count", "recorded_avg", 
                   "diff", "diff_pct", "status")
        
        # Configure tree style with larger font for better checkbox visibility
        style = ttk.Style()
        style.configure("Treeview", font=('Arial', 10), rowheight=25)
        style.configure("Treeview.Heading", font=('Arial', 10, 'bold'))
        
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Track column visibility
        self.column_visibility = {
            "selected": True,
            "row": True,
            "element": True,
            "feedrate": False,  # Hidden by default, available in tooltips
            "sorting_address": False,  # Hidden by default, available in tooltips
            "comment": False,  # Hidden by default, available in tooltips
            "default_total": True,
            "recorded_total": True,
            "default_avg": False,  # Hide average columns for timeline view
            "recorded_count": False,
            "recorded_avg": False,
            "diff": True,
            "diff_pct": True,
            "status": True
        }
        
        # Define column headings
        self.tree.heading("selected", text="□", command=self.toggle_all_selection)
        self.tree.heading("row", text="Row #")
        self.tree.heading("element", text="Command")
        self.tree.heading("feedrate", text="FeedRate")
        self.tree.heading("sorting_address", text="SortingAddress")
        self.tree.heading("comment", text="Comment")
        self.tree.heading("default_total", text="Expected Time (s)")
        self.tree.heading("recorded_total", text="Actual Time (s)")
        self.tree.heading("default_avg", text="")
        self.tree.heading("recorded_count", text="")
        self.tree.heading("recorded_avg", text="")
        self.tree.heading("diff", text="Difference (s)")
        self.tree.heading("diff_pct", text="Diff %")
        self.tree.heading("status", text="Status")
        
        # Define column widths
        self.tree.column("selected", width=60, anchor=tk.CENTER, minwidth=60)
        self.tree.column("row", width=60, anchor=tk.CENTER)
        self.tree.column("element", width=150, anchor=tk.W)
        self.tree.column("feedrate", width=80, anchor=tk.E)
        self.tree.column("sorting_address", width=120, anchor=tk.CENTER)
        self.tree.column("comment", width=200, anchor=tk.W)
        self.tree.column("default_total", width=110, anchor=tk.E)
        self.tree.column("recorded_total", width=110, anchor=tk.E)
        self.tree.column("default_avg", width=100, anchor=tk.E)
        self.tree.column("recorded_count", width=90, anchor=tk.CENTER)
        self.tree.column("recorded_avg", width=100, anchor=tk.E)
        self.tree.column("diff", width=100, anchor=tk.E)
        self.tree.column("diff_pct", width=80, anchor=tk.E)
        self.tree.column("status", width=100, anchor=tk.CENTER)
        
        # Add tooltips to headers
        self.setup_column_tooltips()
        
        # Apply initial column visibility
        self.apply_column_visibility()
        
        # Add scrollbars
        tree_vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_vsb.set, xscrollcommand=tree_hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_vsb.grid(row=0, column=1, sticky="ns")
        tree_hsb.grid(row=1, column=0, sticky="ew")
        
        # Bind click events for selection - use Button and return 'break'
        self.tree.bind('<Button-1>', self.on_tree_click)
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bottom section - Summary and statistics
        summary_frame = ttk.LabelFrame(paned, text="Summary & Statistics", padding="10")
        paned.add(summary_frame, weight=1)
        
        self.summary_text = tk.Text(summary_frame, height=10, font=("Consolas", 10), wrap=tk.WORD)
        summary_scroll = ttk.Scrollbar(summary_frame, orient="vertical", 
                                       command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scroll.set)
        
        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_column_tooltips(self):
        """Setup tooltips for column headers"""
        # Define tooltips for each column
        self.column_tooltips = {
            "selected": "Click this header to select/deselect ALL rows.\n□ = None selected\n■ = All selected\n▣ = Some selected\n\nClick individual row checkboxes (■/□) to select/deselect that row. Hold Shift and click to select range. Only selected rows are included in calculations, visualizations, and exports.",
            "row": "Sequential timeline position (row number in XML file)",
            "element": "NC program command type at this position in the sequence",
            "feedrate": "Feed rate value from XML (optional attribute, can be toggled in Column Settings)",
            "sorting_address": "Sorting address from XML (optional attribute, can be toggled in Column Settings)",
            "comment": "Comment text from XML (optional attribute, can be toggled in Column Settings)",
            "default_total": "Expected time for this specific command in the timeline (from Main section EstTime in seconds)",
            "recorded_total": "Actual recorded time for this command in the timeline (from Sheet Time element in seconds)",
            "default_avg": "",
            "recorded_count": "",
            "recorded_avg": "",
            "diff": "Time difference between actual and expected (positive = slower, negative = faster)",
            "diff_pct": "Percentage difference from expected time",
            "status": "Performance status:\n✓ On Time (within tolerance), ⚠ Slower (exceeds tolerance), ✓ Faster (better than expected), ⚠ Missing (data not present)"
        }
        
        self.tooltip_window = None
        self.tree.bind("<Motion>", self.show_column_tooltip)
        self.tree.bind("<Leave>", self.hide_column_tooltip)
    
    def show_column_tooltip(self, event):
        """Show tooltip when hovering over column headers"""
        region = self.tree.identify_region(event.x, event.y)
        
        if region == "heading":
            column = self.tree.identify_column(event.x)
            column_id = self.tree.column(column, "id")
            
            if column_id in self.column_tooltips:
                # Hide previous tooltip
                self.hide_column_tooltip()
                
                # Create new tooltip
                tooltip_text = self.column_tooltips[column_id]
                x = event.x_root + 10
                y = event.y_root + 10
                
                self.tooltip_window = tw = tk.Toplevel(self.tree)
                tw.wm_overrideredirect(True)
                tw.wm_geometry(f"+{x}+{y}")
                
                label = tk.Label(tw, text=tooltip_text, justify=tk.LEFT,
                                background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                                font=("Arial", 9), padx=8, pady=5, wraplength=350)
                label.pack()
        else:
            self.hide_column_tooltip()
    
    def hide_column_tooltip(self, event=None):
        """Hide the column tooltip"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
        
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select XML File with Sheet Times",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if filename:
            self.load_xml_file(filename)
            
    def load_xml_file(self, xml_file):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            self.xml_file = xml_file
            self.file_label.config(text=os.path.basename(xml_file), foreground="black")
            
            # Get NCProgram name
            self.nc_program_name = root.get("Name", "Unknown Program")
            self.program_label.config(text=f"Program: {self.nc_program_name}")
            
            # Clear previous data
            self.default_times.clear()
            self.sheet_times.clear()
            self.all_sheets.clear()
            self.element_order.clear()
            self.default_timeline.clear()
            self.sheet_timelines.clear()
            
            # Parse Main element for default times (EstTime in seconds)
            main_elem = root.find("Main")
            if main_elem is not None:
                for elem in main_elem.iter():
                    if 'EstTime' in elem.attrib:
                        try:
                            value = float(elem.attrib['EstTime'])
                            # Add to aggregated dict
                            if elem.tag not in self.default_times:
                                self.default_times[elem.tag] = []
                                self.element_order.append(elem.tag)  # Track order
                            self.default_times[elem.tag].append(value)
                            # Add to timeline sequence with additional attributes
                            self.default_timeline.append({
                                'tag': elem.tag,
                                'time': value,
                                'feedrate': elem.attrib.get('FeedRate', ''),
                                'sorting_address': elem.attrib.get('SortingAddress', ''),
                                'comment': elem.attrib.get('Comment', '')
                            })
                        except ValueError:
                            pass
            
            # Parse Sheet elements for recorded times
            sheets_container = root.find("Sheets")
            if sheets_container is not None:
                sheet_index = 1
                for sheet_elem in sheets_container.findall("Sheet"):
                    # Get sheet name or create one based on timestamps
                    sheet_name = sheet_elem.get("Name")
                    if not sheet_name:
                        start_time = sheet_elem.find("StartTime")
                        end_time = sheet_elem.find("EndTime")
                        if start_time is not None and start_time.text:
                            # Use start time as identifier
                            sheet_name = f"Sheet {sheet_index} - {start_time.text}"
                        else:
                            sheet_name = f"Sheet {sheet_index}"
                    
                    self.all_sheets.append(sheet_name)
                    
                    # Parse Time elements (values in milliseconds)
                    sheet_data = defaultdict(list)
                    sheet_timeline = []  # Timeline sequence for this sheet
                    times_elem = sheet_elem.find("Times")
                    if times_elem is not None:
                        for time_elem in times_elem.findall("Time"):
                            command = time_elem.get("Command")
                            if command and time_elem.text:
                                try:
                                    # Convert milliseconds to seconds
                                    value_ms = float(time_elem.text)
                                    value_sec = value_ms / 1000.0
                                    # Add to aggregated dict
                                    sheet_data[command].append(value_sec)
                                    # Add to timeline sequence with additional attributes
                                    sheet_timeline.append({
                                        'tag': command,
                                        'time': value_sec,
                                        'feedrate': time_elem.get('FeedRate', ''),
                                        'sorting_address': time_elem.get('SortingAddress', ''),
                                        'comment': time_elem.get('Comment', '')
                                    })
                                except ValueError:
                                    pass
                    
                    self.sheet_times[sheet_name] = dict(sheet_data)
                    self.sheet_timelines[sheet_name] = sheet_timeline
                    
                    # Store metadata
                    start_time = sheet_elem.find("StartTime")
                    end_time = sheet_elem.find("EndTime")
                    self.sheet_metadata[sheet_name] = {
                        'start': start_time.text if start_time is not None and start_time.text else "N/A",
                        'end': end_time.text if end_time is not None and end_time.text else "N/A"
                    }
                    
                    sheet_index += 1
            
            # Update sheet selector
            if self.all_sheets:
                self.sheet_combo['values'] = self.all_sheets
                self.sheet_combo.current(0)
                self.display_sheet_comparison()
            else:
                messagebox.showwarning("No Sheets Found", 
                                       "No Sheet elements found in the XML file")
            
            msg = f"Loaded successfully:\n"
            msg += f"• Default times from Main: {len(self.default_times)} element types\n"
            msg += f"• Total default time: {sum(sum(times) for times in self.default_times.values()):.3f} seconds\n"
            msg += f"• Sheets found: {len(self.all_sheets)}\n\n"
            if self.all_sheets:
                msg += "Sheets:\n"
                for sheet in self.all_sheets:
                    msg += f"  - {sheet}\n"
            messagebox.showinfo("File Loaded", msg)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load XML file:\n{str(e)}")
            
    def display_sheet_comparison(self):
        """Display timeline-based comparison for the selected sheet"""
        if not self.sheet_var.get():
            return
            
        sheet_name = self.sheet_var.get()
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get timeline data
        expected_timeline = self.default_timeline
        actual_timeline = self.sheet_timelines.get(sheet_name, [])
        
        comparison_data = []
        default_total = 0
        recorded_total = 0
        
        # Determine maximum rows to compare
        max_rows = max(len(expected_timeline), len(actual_timeline))
        
        for i in range(max_rows):
            # Get expected and actual for this row
            expected_data = expected_timeline[i] if i < len(expected_timeline) else {}
            expected_cmd = expected_data.get('tag') if expected_data else None
            expected_time = expected_data.get('time', 0) if expected_data else 0
            expected_feedrate = expected_data.get('feedrate', '') if expected_data else ''
            expected_sorting = expected_data.get('sorting_address', '') if expected_data else ''
            expected_comment = expected_data.get('comment', '') if expected_data else ''
            
            actual_data = actual_timeline[i] if i < len(actual_timeline) else {}
            actual_cmd = actual_data.get('tag') if actual_data else None
            actual_time = actual_data.get('time', 0) if actual_data else 0
            actual_feedrate = actual_data.get('feedrate', '') if actual_data else ''
            actual_sorting = actual_data.get('sorting_address', '') if actual_data else ''
            actual_comment = actual_data.get('comment', '') if actual_data else ''
            
            # Calculate difference
            diff = actual_time - expected_time
            diff_pct = ((actual_time - expected_time) / expected_time * 100) if expected_time > 0 else 0
            
            # Determine status using the tolerance value
            tolerance = self.tolerance_var.get()
            if expected_time == 0 or actual_time == 0:
                # Missing data
                status = "⚠ Missing"
                tag = "missing"
            elif abs(diff_pct) <= tolerance:
                status = "✓ On Time"
                tag = "ontime"
            elif diff > 0:
                status = "⚠ Slower"
                tag = "slower"
            else:
                status = "✓ Faster"
                tag = "faster"
            
            default_total += expected_time
            recorded_total += actual_time
            
            # Check if commands match
            cmd_match = (expected_cmd == actual_cmd) if (expected_cmd and actual_cmd) else False
            display_element = expected_cmd if expected_cmd else actual_cmd
            if not cmd_match and expected_cmd and actual_cmd:
                display_element = f"{expected_cmd} / {actual_cmd}"
            
            # Use actual values if available, otherwise expected
            display_feedrate = actual_feedrate if actual_feedrate else expected_feedrate
            display_sorting = actual_sorting if actual_sorting else expected_sorting
            display_comment = actual_comment if actual_comment else expected_comment
            
            comparison_data.append({
                'row': i + 1,
                'element': display_element,
                'feedrate': display_feedrate,
                'sorting_address': display_sorting,
                'comment': display_comment,
                'expected_cmd': expected_cmd,
                'expected_time': expected_time,
                'actual_cmd': actual_cmd,
                'actual_time': actual_time,
                'diff': diff,
                'diff_pct': diff_pct,
                'status': status,
                'tag': tag,
                'cmd_match': cmd_match,
                'selected': True  # Default to selected
            })
        
        # Store for filtering and summary
        self.current_comparison_data = comparison_data
        self.current_default_total = default_total
        self.current_recorded_total = recorded_total
        
        # Populate treeview with filtering applied
        self.populate_treeview()
        
        # Update summary
        self.update_summary(sheet_name, default_total, recorded_total, comparison_data)
    
    def populate_treeview(self):
        """Populate treeview with timeline comparison data and filters"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not self.current_comparison_data:
            return
        
        # Apply status filters
        show_faster = self.filter_faster.get()
        show_ontime = self.filter_ontime.get()
        show_slower = self.filter_slower.get()
        
        # Populate treeview with filtered data
        for data in self.current_comparison_data:
            # Apply filter based on status
            if data['tag'] == 'faster' and not show_faster:
                continue
            elif data['tag'] == 'ontime' and not show_ontime:
                continue
            elif data['tag'] == 'slower' and not show_slower:
                continue
            elif data['tag'] == 'missing':
                # Always show missing entries
                pass
            
            # Format display values - use larger checkbox characters
            checkbox = "■" if data.get('selected', True) else "□"
            values = (
                checkbox,
                f"Row {data['row']}",  # Show row number instead of element name
                data['element'],  # Command name
                data.get('feedrate', ''),  # FeedRate
                data.get('sorting_address', ''),  # SortingAddress
                data.get('comment', ''),  # Comment
                f"{data['expected_time']:.3f}" if data['expected_time'] > 0 else "-",
                f"{data['actual_time']:.3f}" if data['actual_time'] > 0 else "-",
                "",  # Empty columns for avg
                "",
                "",
                f"{data['diff']:+.3f}" if (data['expected_time'] > 0 and data['actual_time'] > 0) else "-",
                f"{data['diff_pct']:+.1f}%" if (data['expected_time'] > 0 and data['actual_time'] > 0) else "-",
                data['status']
            )
            
            # Add special tag if commands don't match
            tags = [data['tag']]
            if not data['cmd_match'] and data['expected_cmd'] and data['actual_cmd']:
                tags.append('mismatch')
            
            self.tree.insert("", tk.END, values=values, tags=tuple(tags))
        
        # Configure tags for colors
        self.tree.tag_configure("faster", foreground="green")
        self.tree.tag_configure("slower", foreground="red")
        self.tree.tag_configure("ontime", foreground="blue")
        self.tree.tag_configure("missing", foreground="orange")
        self.tree.tag_configure("mismatch", background="#ffe6e6")  # Light red background for mismatches
        
        # Update selection count label
        self.update_selection_count()
    
    def update_selection_count(self):
        """Update the selection count label and header checkbox"""
        if not self.current_comparison_data:
            self.selection_label.config(text="Selected: 0/0")
            self.tree.heading("selected", text="□")
            return
        
        selected_count = sum(1 for d in self.current_comparison_data if d.get('selected', True))
        total_count = len(self.current_comparison_data)
        self.selection_label.config(text=f"Selected: {selected_count}/{total_count}")
        
        # Update header checkbox to reflect current state
        if selected_count == total_count:
            self.tree.heading("selected", text="■")  # All selected
        elif selected_count == 0:
            self.tree.heading("selected", text="□")  # None selected
        else:
            self.tree.heading("selected", text="▣")  # Some selected (indeterminate)
    
    def on_tree_click(self, event):
        """Handle click on treeview to toggle selection"""
        try:
            region = self.tree.identify('region', event.x, event.y)
            
            # Allow heading clicks to pass through to their command handlers
            if region == "heading":
                return  # Don't return 'break', let the heading command execute
            
            # Check if Shift key is pressed
            if event.state & 0x0001:  # Shift key
                return self.on_shift_click(event)
            
            item = self.tree.identify_row(event.y)
            column = self.tree.identify_column(event.x)
            
            if not item or not self.current_comparison_data:
                return 'break'
            
            # Only handle clicks on the first column (checkbox column)
            if column != '#1':
                return 'break'  # Still prevent default selection behavior
            
            # Get the row index from visible items
            visible_items = self.tree.get_children()
            if item not in visible_items:
                return 'break'
            
            row_index = visible_items.index(item)
            
            # Find corresponding data in comparison_data (accounting for filters)
            visible_data_indices = []
            show_faster = self.filter_faster.get()
            show_ontime = self.filter_ontime.get()
            show_slower = self.filter_slower.get()
            
            for idx, data in enumerate(self.current_comparison_data):
                if data['tag'] == 'faster' and not show_faster:
                    continue
                elif data['tag'] == 'ontime' and not show_ontime:
                    continue
                elif data['tag'] == 'slower' and not show_slower:
                    continue
                visible_data_indices.append(idx)
            
            if row_index >= len(visible_data_indices):
                return 'break'
            
            data_index = visible_data_indices[row_index]
            
            # Toggle selection
            self.current_comparison_data[data_index]['selected'] = not self.current_comparison_data[data_index].get('selected', True)
            self.last_selected_index = data_index
            
            # Refresh display
            self.populate_treeview()
            self.update_summary_with_selection()
            
            return 'break'  # Prevent default treeview selection
        except Exception as e:
            print(f"Click error: {e}")
            import traceback
            traceback.print_exc()
            return 'break'
    
    def on_shift_click(self, event):
        """Handle Shift+click for range selection"""
        try:
            region = self.tree.identify('region', event.x, event.y)
            
            # Allow heading clicks to pass through to their command handlers
            if region == "heading":
                return  # Don't return 'break', let the heading command execute
            
            item = self.tree.identify_row(event.y)
            column = self.tree.identify_column(event.x)
            
            if not item or not self.current_comparison_data:
                return 'break'
            
            # Only handle clicks on the first column (checkbox column)
            if column != '#1':
                return 'break'
            
            # Get the row index from visible items
            visible_items = self.tree.get_children()
            if item not in visible_items:
                return 'break'
            
            row_index = visible_items.index(item)
            
            # Find corresponding data indices
            visible_data_indices = []
            show_faster = self.filter_faster.get()
            show_ontime = self.filter_ontime.get()
            show_slower = self.filter_slower.get()
            
            for idx, data in enumerate(self.current_comparison_data):
                if data['tag'] == 'faster' and not show_faster:
                    continue
                elif data['tag'] == 'ontime' and not show_ontime:
                    continue
                elif data['tag'] == 'slower' and not show_slower:
                    continue
                visible_data_indices.append(idx)
            
            if row_index >= len(visible_data_indices):
                return 'break'
            
            data_index = visible_data_indices[row_index]
            
            # If we have a previous selection, select all between
            if self.last_selected_index is not None:
                start = min(self.last_selected_index, data_index)
                end = max(self.last_selected_index, data_index)
                
                # Determine the selection state from the last selected item
                selection_state = self.current_comparison_data[self.last_selected_index].get('selected', True)
                
                # Set all items in range to the same state
                for i in range(start, end + 1):
                    self.current_comparison_data[i]['selected'] = selection_state
            else:
                # No previous selection, just toggle this one
                self.current_comparison_data[data_index]['selected'] = not self.current_comparison_data[data_index].get('selected', True)
            
            self.last_selected_index = data_index
            
            # Refresh display
            self.populate_treeview()
            self.update_summary_with_selection()
            
            return 'break'  # Prevent default treeview selection
        except Exception as e:
            print(f"Shift-click error: {e}")
            import traceback
            traceback.print_exc()
            return 'break'
    
    def select_all_rows(self):
        """Select all rows"""
        for data in self.current_comparison_data:
            data['selected'] = True
        self.populate_treeview()
        self.update_summary_with_selection()
    
    def deselect_all_rows(self):
        """Deselect all rows"""
        for data in self.current_comparison_data:
            data['selected'] = False
        self.populate_treeview()
        self.update_summary_with_selection()
    
    def toggle_all_selection(self):
        """Toggle all selections when clicking the checkbox header"""
        if not self.current_comparison_data:
            return
        
        # Check if ANY are selected
        any_selected = any(d.get('selected', True) for d in self.current_comparison_data)
        
        # If any are selected, deselect all; otherwise select all
        new_state = not any_selected
        for data in self.current_comparison_data:
            data['selected'] = new_state
        
        self.populate_treeview()
        self.update_summary_with_selection()
    
    def apply_status_filter(self):
        """Apply status filter when checkboxes change"""
        if hasattr(self, 'current_comparison_data') and self.current_comparison_data:
            self.populate_treeview()
    
    def update_tolerance(self):
        """Update the OnTime tolerance and recalculate comparison"""
        if hasattr(self, 'sheet_var') and self.sheet_var.get():
            # Recalculate with new tolerance
            self.display_sheet_comparison()
        
    def update_summary(self, sheet_name, default_total, recorded_total, comparison_data):
        """Update the summary text area - initial load with all data"""
        self.update_summary_with_selection()
    
    def update_summary_with_selection(self):
        """Update the summary text area based on selected rows"""
        if not self.current_comparison_data:
            return
        
        # Get currently selected sheet
        sheet_name = self.sheet_var.get() if hasattr(self, 'sheet_var') else "Unknown"
        
        # Filter to only selected rows
        selected_data = [d for d in self.current_comparison_data if d.get('selected', True)]
        
        # Calculate totals for selected rows
        default_total = sum(d['expected_time'] for d in selected_data)
        recorded_total = sum(d['actual_time'] for d in selected_data)
        
        self.summary_text.delete(1.0, tk.END)
        
        time_diff = recorded_total - default_total
        time_diff_pct = (time_diff / default_total * 100) if default_total > 0 else 0
        
        # Get sheet metadata
        metadata = self.sheet_metadata.get(sheet_name, {'start': 'N/A', 'end': 'N/A'})
        
        summary = f"NC PROGRAM: {self.nc_program_name}\n"
        summary += f"SHEET: {sheet_name}\n"
        summary += "=" * 80 + "\n\n"
        summary += f"Start Time: {metadata['start']}\n"
        summary += f"End Time:   {metadata['end']}\n\n"
        
        # Show selection info
        selected_count = len(selected_data)
        total_count = len(self.current_comparison_data)
        if selected_count < total_count:
            summary += f"SHOWING SELECTED ROWS: {selected_count} of {total_count}\n\n"
        
        summary += f"Default (Main) Total Time:    {default_total:>10.3f} seconds (EstTime attributes)\n"
        summary += f"Recorded (Sheet) Total Time:  {recorded_total:>10.3f} seconds (from Time elements)\n"
        summary += f"Difference:                   {time_diff:>+10.3f} seconds ({time_diff_pct:+.1f}%)\n\n"
        
        # Time in minutes for easier reading
        default_min = int(default_total // 60)
        default_sec = default_total % 60
        recorded_min = int(recorded_total // 60)
        recorded_sec = recorded_total % 60
        
        summary += f"Default Time:  {default_min}m {default_sec:.1f}s\n"
        summary += f"Recorded Time: {recorded_min}m {recorded_sec:.1f}s\n\n"
        
        # Get current tolerance
        tolerance = self.tolerance_var.get()
        
        # Performance assessment
        if abs(time_diff_pct) <= tolerance:
            summary += f"Performance: ✓ EXCELLENT - Within {tolerance}% tolerance\n"
        elif time_diff_pct > tolerance and time_diff_pct <= tolerance * 2:
            summary += f"Performance: ⚠ ACCEPTABLE - Slightly slower than expected\n"
        elif time_diff_pct > tolerance * 2:
            summary += f"Performance: ✗ NEEDS ATTENTION - Significantly slower\n"
        elif time_diff_pct < -tolerance:
            summary += f"Performance: ✓ EXCELLENT - Faster than expected\n"
        
        summary += "\n" + "-" * 80 + "\n"
        summary += f"Element Statistics (tolerance: ±{tolerance}%):\n"
        
        faster_count = sum(1 for d in selected_data if d['diff'] < -0.001)
        slower_count = sum(1 for d in selected_data if d['diff'] > 0.001)
        ontime_count = len(selected_data) - faster_count - slower_count
        
        summary += f"  Faster than expected:  {faster_count}\n"
        summary += f"  Slower than expected:  {slower_count}\n"
        summary += f"  On time (±{tolerance}%):        {ontime_count}\n"
        
        self.summary_text.insert(1.0, summary)
        
    def show_all_sheets_summary(self):
        """Show a summary of all sheets in a new window"""
        if not self.all_sheets:
            messagebox.showwarning("No Data", "No sheets loaded")
            return
        
        # Create new window
        summary_window = tk.Toplevel(self.root)
        summary_window.title("All Sheets Summary")
        summary_window.geometry("1000x600")
        
        # Add program name header
        header_frame = ttk.Frame(summary_window, padding="10")
        header_frame.pack(fill=tk.X)
        ttk.Label(header_frame, text=f"NC Program: {self.nc_program_name}", 
                  font=("Arial", 11, "bold"), foreground="navy").pack()
        
        # Create treeview for all sheets
        frame = ttk.Frame(summary_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("sheet", "expected_total", "actual_total", "diff", "diff_pct", "status")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        
        tree.heading("sheet", text="Sheet Name")
        tree.heading("expected_total", text="Expected Total (s)")
        tree.heading("actual_total", text="Actual Total (s)")
        tree.heading("diff", text="Difference (s)")
        tree.heading("diff_pct", text="Diff %")
        tree.heading("status", text="Status")
        
        tree.column("sheet", width=250, anchor=tk.W)
        tree.column("expected_total", width=120, anchor=tk.E)
        tree.column("actual_total", width=120, anchor=tk.E)
        tree.column("diff", width=120, anchor=tk.E)
        tree.column("diff_pct", width=100, anchor=tk.E)
        tree.column("status", width=150, anchor=tk.CENTER)
        
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Calculate totals for each sheet
        default_grand_total = sum(sum(times) for times in self.default_times.values())
        tolerance = self.tolerance_var.get()
        
        for sheet_name in self.all_sheets:
            recorded_times = self.sheet_times.get(sheet_name, {})
            recorded_total = sum(sum(times) for times in recorded_times.values())
            
            diff = recorded_total - default_grand_total
            diff_pct = (diff / default_grand_total * 100) if default_grand_total > 0 else 0
            
            if abs(diff_pct) <= tolerance:
                status = "✓ On Time"
                tag = "ontime"
            elif diff > 0:
                status = "⚠ Slower"
                tag = "slower"
            else:
                status = "✓ Faster"
                tag = "faster"
            
            values = (
                sheet_name,
                f"{default_grand_total:.3f}",
                f"{recorded_total:.3f}",
                f"{diff:+.3f}",
                f"{diff_pct:+.1f}%",
                status
            )
            
            tree.insert("", tk.END, values=values, tags=(tag,))
        
        tree.tag_configure("faster", foreground="green")
        tree.tag_configure("slower", foreground="red")
        tree.tag_configure("ontime", foreground="blue")
        
    def export_report(self):
        """Export detailed comparison report for selected rows"""
        if not self.current_comparison_data or not self.sheet_var.get():
            messagebox.showwarning("No Data", "Please select a sheet first")
            return
        
        # Suggest filename based on NC Program name and sheet name
        sheet_name = self.sheet_var.get()
        safe_sheet_name = sheet_name.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_')
        safe_program_name = self.nc_program_name.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_')
        suggested_name = f"{safe_program_name}_{safe_sheet_name}.txt"
        
        initial_dir = os.path.dirname(self.xml_file) if self.xml_file else None
        
        filename = filedialog.asksaveasfilename(
            title="Export Report",
            defaultextension=".txt",
            initialfile=suggested_name,
            initialdir=initial_dir,
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        selected_data = [d for d in self.current_comparison_data if d.get('selected', True)]
        
        if not selected_data:
            messagebox.showwarning("No Selection", "No rows selected to export")
            return
        
        try:
            # Determine format from extension
            is_csv = filename.lower().endswith('.csv')
            delimiter = ',' if is_csv else '\t'
            
            with open(filename, 'w', encoding='utf-8') as f:
                if not is_csv:
                    f.write("SHEET TIMES COMPARISON REPORT\n")
                    f.write("=" * 100 + "\n\n")
                    f.write(f"NC Program: {self.nc_program_name}\n")
                    f.write(f"Sheet: {sheet_name}\n")
                    f.write(f"Source File: {self.xml_file}\n")
                    f.write(f"Selected Rows: {len(selected_data)} of {len(self.current_comparison_data)}\n\n")
                
                # Header
                if is_csv:
                    f.write("Row,Command,Expected Time (s),Actual Time (s),Difference (s),Diff %,Status\n")
                else:
                    f.write(f"{'Row':<6} {'Command':<25} {'Expected':>12} {'Actual':>12} {'Difference':>12} {'Diff %':>10} {'Status':>15}\n")
                    f.write("-" * 100 + "\n")
                
                # Data rows
                default_total = 0
                recorded_total = 0
                
                for data in selected_data:
                    default_total += data['expected_time']
                    recorded_total += data['actual_time']
                    
                    if is_csv:
                        f.write(f"{data['row']},{data['element']},{data['expected_time']:.3f},"
                               f"{data['actual_time']:.3f},{data['diff']:+.3f},"
                               f"{data['diff_pct']:+.1f},{data['status']}\n")
                    else:
                        f.write(f"{data['row']:<6} {data['element']:<25} {data['expected_time']:>12.3f} "
                               f"{data['actual_time']:>12.3f} {data['diff']:>+12.3f} "
                               f"{data['diff_pct']:>+9.1f}% {data['status']:>15}\n")
                
                # Totals
                if not is_csv:
                    f.write("-" * 100 + "\n")
                    diff = recorded_total - default_total
                    diff_pct = (diff / default_total * 100) if default_total > 0 else 0
                    f.write(f"{'TOTAL':<6} {'':<25} {default_total:>12.3f} {recorded_total:>12.3f} "
                           f"{diff:>+12.3f} {diff_pct:>+9.1f}%\n")
            
            messagebox.showinfo("Export Complete", f"Report exported to:\n{filename}\n\n"
                              f"Selected rows: {len(selected_data)}")
            
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export report:\n{str(e)}")
    
    def export_multiple_sheets(self):
        """Export reports for multiple selected sheets"""
        if not self.all_sheets:
            messagebox.showwarning("No Sheets", "No sheets available to export")
            return
        
        # Create sheet selection dialog
        select_window = tk.Toplevel(self.root)
        select_window.title("Select Sheets to Export")
        select_window.geometry("500x600")
        select_window.transient(self.root)
        select_window.grab_set()
        
        # Header
        header_frame = ttk.Frame(select_window, padding="10")
        header_frame.pack(fill=tk.X)
        ttk.Label(header_frame, text="Select sheets to export:", 
                 font=("Arial", 11, "bold")).pack(anchor=tk.W)
        ttk.Label(header_frame, text=f"NC Program: {self.nc_program_name}", 
                 font=("Arial", 9), foreground="navy").pack(anchor=tk.W, pady=5)
        
        # Buttons for select all/none
        button_frame = ttk.Frame(select_window, padding="5")
        button_frame.pack(fill=tk.X)
        
        sheet_vars = {}
        
        def select_all():
            for var in sheet_vars.values():
                var.set(True)
        
        def select_none():
            for var in sheet_vars.values():
                var.set(False)
        
        ttk.Button(button_frame, text="Select All", command=select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Select None", command=select_none).pack(side=tk.LEFT, padx=5)
        
        # Scrollable frame for sheets
        canvas = tk.Canvas(select_window)
        scrollbar = ttk.Scrollbar(select_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create checkboxes for each sheet
        for sheet_name in self.all_sheets:
            var = tk.BooleanVar(value=True)  # Default all selected
            sheet_vars[sheet_name] = var
            
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill=tk.X, padx=10, pady=2)
            
            cb = ttk.Checkbutton(frame, text=sheet_name, variable=var)
            cb.pack(side=tk.LEFT)
            
            # Show row count if available
            if sheet_name in self.sheet_timelines:
                count = len(self.sheet_timelines[sheet_name])
                ttk.Label(frame, text=f"({count} rows)", foreground="gray").pack(side=tk.LEFT, padx=5)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Format selection
        format_frame = ttk.LabelFrame(select_window, text="Export Format", padding="10")
        format_frame.pack(fill=tk.X, padx=10, pady=5)
        
        format_var = tk.StringVar(value="txt")
        ttk.Radiobutton(format_frame, text="Text (.txt)", variable=format_var, value="txt").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="CSV (.csv)", variable=format_var, value="csv").pack(side=tk.LEFT, padx=10)
        
        # Bottom buttons
        bottom_frame = ttk.Frame(select_window, padding="10")
        bottom_frame.pack(fill=tk.X)
        
        def do_export():
            selected_sheets = [name for name, var in sheet_vars.items() if var.get()]
            
            if not selected_sheets:
                messagebox.showwarning("No Selection", "Please select at least one sheet to export")
                return
            
            # Ask for directory
            directory = filedialog.askdirectory(
                title="Select Directory for Export",
                initialdir=os.path.dirname(self.xml_file) if self.xml_file else None
            )
            
            if not directory:
                return
            
            select_window.destroy()
            
            # Export each selected sheet
            exported_files = []
            failed_sheets = []
            
            for sheet_name in selected_sheets:
                try:
                    # Generate filename based on NC Program name
                    safe_sheet_name = sheet_name.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_')
                    safe_program_name = self.nc_program_name.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_')
                    
                    extension = "." + format_var.get()
                    filename = os.path.join(directory, f"{safe_program_name}_{safe_sheet_name}{extension}")
                    
                    # Get data for this sheet
                    sheet_data = self._build_comparison_data(sheet_name)
                    
                    if not sheet_data:
                        failed_sheets.append((sheet_name, "No data available"))
                        continue
                    
                    # Export the sheet
                    self._export_sheet_to_file(filename, sheet_name, sheet_data, format_var.get())
                    exported_files.append(filename)
                    
                except Exception as e:
                    failed_sheets.append((sheet_name, str(e)))
            
            # Show results
            result_msg = f"Exported {len(exported_files)} sheet(s) to:\n{directory}\n\n"
            
            if exported_files:
                result_msg += "Files created:\n"
                for f in exported_files:
                    result_msg += f"• {os.path.basename(f)}\n"
            
            if failed_sheets:
                result_msg += f"\n{len(failed_sheets)} sheet(s) failed:\n"
                for sheet, error in failed_sheets:
                    result_msg += f"• {sheet}: {error}\n"
            
            if failed_sheets:
                messagebox.showwarning("Export Complete with Errors", result_msg)
            else:
                messagebox.showinfo("Export Complete", result_msg)
        
        ttk.Button(bottom_frame, text="Export", command=do_export).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="Cancel", command=select_window.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Center the dialog
        select_window.update_idletasks()
        x = (select_window.winfo_screenwidth() // 2) - (select_window.winfo_width() // 2)
        y = (select_window.winfo_screenheight() // 2) - (select_window.winfo_height() // 2)
        select_window.geometry(f"+{x}+{y}")
    
    def _build_comparison_data(self, sheet_name):
        """Build comparison data for a specific sheet"""
        if sheet_name not in self.sheet_timelines:
            return []
        
        comparison_data = []
        
        # Get timeline data
        expected_timeline = self.default_timeline
        actual_timeline = self.sheet_timelines.get(sheet_name, [])
        
        # Determine maximum rows to compare
        max_rows = max(len(expected_timeline), len(actual_timeline))
        
        for i in range(max_rows):
            # Get expected and actual for this row
            expected_data = expected_timeline[i] if i < len(expected_timeline) else {}
            expected_cmd = expected_data.get('tag') if expected_data else None
            expected_time = expected_data.get('time', 0) if expected_data else 0
            
            actual_data = actual_timeline[i] if i < len(actual_timeline) else {}
            actual_cmd = actual_data.get('tag') if actual_data else None
            actual_time = actual_data.get('time', 0) if actual_data else 0
            
            # Calculate difference
            diff = actual_time - expected_time
            diff_pct = ((actual_time - expected_time) / expected_time * 100) if expected_time > 0 else 0
            
            # Determine status using the tolerance value
            tolerance = self.tolerance_var.get() if hasattr(self, 'tolerance_var') else 5.0
            if expected_time == 0 or actual_time == 0:
                # Missing data
                status = "Missing"
                tag = "missing"
            elif abs(diff_pct) <= tolerance:
                status = "On Time"
                tag = "ontime"
            elif diff > 0:
                status = "Slower"
                tag = "slower"
            else:
                status = "Faster"
                tag = "faster"
            
            # Check if commands match
            cmd_match = (expected_cmd == actual_cmd) if (expected_cmd and actual_cmd) else False
            display_element = expected_cmd if expected_cmd else actual_cmd
            if not cmd_match and expected_cmd and actual_cmd:
                display_element = f"{expected_cmd} / {actual_cmd}"
            
            comparison_data.append({
                'row': i + 1,
                'element': display_element,
                'expected_time': expected_time,
                'actual_time': actual_time,
                'diff': diff,
                'diff_pct': diff_pct,
                'status': status,
                'tag': tag,
                'selected': True
            })
        
        return comparison_data
    
    def _export_sheet_to_file(self, filename, sheet_name, sheet_data, format_type):
        """Export a single sheet's data to a file"""
        is_csv = format_type == 'csv'
        delimiter = ',' if is_csv else '\t'
        
        with open(filename, 'w', encoding='utf-8') as f:
            if not is_csv:
                f.write("SHEET TIMES COMPARISON REPORT\n")
                f.write("=" * 100 + "\n\n")
                f.write(f"NC Program: {self.nc_program_name}\n")
                f.write(f"Sheet: {sheet_name}\n")
                f.write(f"Source File: {self.xml_file}\n")
                f.write(f"Selected Rows: {len(sheet_data)} of {len(sheet_data)}\n\n")
            
            # Header
            if is_csv:
                f.write("Row,Command,Expected Time (s),Actual Time (s),Difference (s),Diff %,Status\n")
            else:
                f.write(f"{'Row':<6} {'Command':<25} {'Expected':>12} {'Actual':>12} {'Difference':>12} {'Diff %':>10} {'Status':>15}\n")
                f.write("-" * 100 + "\n")
            
            # Data rows
            default_total = 0
            recorded_total = 0
            
            for data in sheet_data:
                default_total += data['expected_time']
                recorded_total += data['actual_time']
                
                if is_csv:
                    f.write(f"{data['row']},{data['element']},{data['expected_time']:.3f},"
                           f"{data['actual_time']:.3f},{data['diff']:+.3f},"
                           f"{data['diff_pct']:+.1f},{data['status']}\n")
                else:
                    f.write(f"{data['row']:<6} {data['element']:<25} {data['expected_time']:>12.3f} "
                           f"{data['actual_time']:>12.3f} {data['diff']:>+12.3f} "
                           f"{data['diff_pct']:>+9.1f}% {data['status']:>15}\n")
            
            # Totals
            if not is_csv:
                f.write("-" * 100 + "\n")
                diff = recorded_total - default_total
                diff_pct = (diff / default_total * 100) if default_total > 0 else 0
                f.write(f"{'TOTAL':<6} {'':<25} {default_total:>12.3f} {recorded_total:>12.3f} "
                       f"{diff:>+12.3f} {diff_pct:>+9.1f}%\n")
    
    def show_column_settings(self):
        """Show dialog to control column visibility"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Column Visibility Settings")
        settings_window.geometry("400x500")
        
        frame = ttk.Frame(settings_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Select columns to display:", 
                  font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # Column display names
        column_names = {
            "selected": "□ Checkbox",
            "row": "Row #",
            "element": "Command",
            "default_total": "Expected Time",
            "recorded_total": "Actual Time",
            "default_avg": "(unused)",
            "recorded_count": "(unused)",
            "recorded_avg": "(unused)",
            "diff": "Difference",
            "diff_pct": "Difference %",
            "status": "Status"
        }
        
        checkbox_vars = {}
        
        for col_id, col_name in column_names.items():
            # Skip unused columns
            if col_name == "(unused)":
                continue
                
            var = tk.BooleanVar(value=self.column_visibility[col_id])
            checkbox_vars[col_id] = var
            cb = ttk.Checkbutton(frame, text=col_name, variable=var)
            cb.pack(anchor=tk.W, pady=2)
            
            # Selected, Row #, and Command should always be visible
            if col_id in ["selected", "row", "element"]:
                cb.config(state="disabled")
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20, fill=tk.X)
        
        def apply_settings():
            for col_id, var in checkbox_vars.items():
                if col_id != "element":  # Element column always visible
                    self.column_visibility[col_id] = var.get()
            self.apply_column_visibility()
            settings_window.destroy()
        
        def select_all():
            for col_id, var in checkbox_vars.items():
                if col_id != "element":
                    var.set(True)
        
        def deselect_all():
            for col_id, var in checkbox_vars.items():
                if col_id != "element":
                    var.set(False)
        
        ttk.Button(button_frame, text="Select All", 
                   command=select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Deselect All", 
                   command=deselect_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Apply", 
                   command=apply_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                   command=settings_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def apply_column_visibility(self):
        """Apply column visibility settings to the treeview"""
        # Always include 'selected' column first
        all_columns = ["selected", "row", "element", "feedrate", "sorting_address", "comment",
                       "default_total", "recorded_total",
                       "default_avg", "recorded_count", "recorded_avg", 
                       "diff", "diff_pct", "status"]
        
        visible_columns = [col for col in all_columns if self.column_visibility.get(col, True)]
        
        self.tree["displaycolumns"] = visible_columns
    
    def show_chart_selection(self):
        """Show dialog to select which charts to create"""
        selection_window = tk.Toplevel(self.root)
        selection_window.title("Select Charts to Create")
        selection_window.geometry("500x550")
        
        frame = ttk.Frame(selection_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Select charts to create when you click Visualize:", 
                  font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(frame, text="Your selections will be remembered for this session.", 
                  font=("Arial", 9), foreground="gray").pack(anchor=tk.W, pady=(0, 15))
        
        # Chart display names and descriptions
        chart_info = {
            'chart1_comparison': ("1. Expected vs Actual Bar Chart", 
                                  "Side-by-side comparison of time values"),
            'chart2_difference': ("2. Time Difference Bar Chart", 
                                  "Shows difference from expected (colored by status)"),
            'chart3_percentage': ("3. Percentage Difference Line Chart", 
                                  "Percentage deviation with tolerance lines"),
            'chart4_status': ("4. Status Distribution Pie Chart", 
                             "Overall status breakdown"),
            'chart6_cumulative': ("5. Cumulative Time Progress", 
                                 "Expected vs Actual with cumulative diff %"),
            'chart7_waterfall': ("6. Waterfall Chart ⭐", 
                                "Cumulative difference breakdown (shows contributors)"),
            'chart8_dual_timeline': ("7. Synchronized Dual Timeline ⭐", 
                                    "Side-by-side timelines with difference bars")
        }
        
        checkbox_vars = {}
        
        for chart_id, (name, desc) in chart_info.items():
            var = tk.BooleanVar(value=self.chart_selections[chart_id])
            checkbox_vars[chart_id] = var
            
            cb_frame = ttk.Frame(frame)
            cb_frame.pack(anchor=tk.W, pady=3, fill=tk.X)
            
            cb = ttk.Checkbutton(cb_frame, text=name, variable=var)
            cb.pack(anchor=tk.W)
            
            desc_label = ttk.Label(cb_frame, text=f"   {desc}", 
                                  font=("Arial", 8), foreground="gray")
            desc_label.pack(anchor=tk.W, padx=(20, 0))
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20, fill=tk.X)
        
        def apply_settings():
            # Count selected
            selected_count = 0
            for chart_id, var in checkbox_vars.items():
                self.chart_selections[chart_id] = var.get()
                if var.get():
                    selected_count += 1
            
            if selected_count == 0:
                messagebox.showwarning("No Charts Selected", 
                                     "Please select at least one chart to create.")
                return
            
            selection_window.destroy()
            messagebox.showinfo("Chart Selection Saved", 
                              f"{selected_count} chart(s) selected.\n\n"
                              f"Click 'Visualize' to create the selected charts.")
        
        def select_all():
            for var in checkbox_vars.values():
                var.set(True)
        
        def deselect_all():
            for var in checkbox_vars.values():
                var.set(False)
        
        ttk.Button(button_frame, text="Select All", 
                   command=select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Deselect All", 
                   command=deselect_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Apply", 
                   command=apply_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                   command=selection_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def create_visualization(self):
        """Create separate interactive graphs of the comparison results"""
        if not self.current_comparison_data or not self.sheet_var.get():
            messagebox.showwarning("No Data", "Please select a sheet first")
            return
        
        sheet_name = self.sheet_var.get()
        
        try:
            # Enable interactive mode
            plt.ion()
            
            # Prepare data for visualization - only selected rows
            elements = []
            expected_totals = []
            actual_totals = []
            differences = []
            diff_percentages = []
            colors = []
            
            selected_data = [d for d in self.current_comparison_data if d.get('selected', True)]
            
            if not selected_data:
                messagebox.showwarning("No Selection", "No rows are selected. Please select rows to visualize.")
                return
            
            for data in selected_data:
                elements.append(data['element'])  # Show command name (e.g., LASER_START, MOVE)
                expected_totals.append(data['expected_time'])
                actual_totals.append(data['actual_time'])
                differences.append(data['diff'])
                diff_percentages.append(data['diff_pct'])
                
                # Color based on status
                if data['tag'] == 'faster':
                    colors.append('green')
                elif data['tag'] == 'slower':
                    colors.append('red')
                elif data['tag'] == 'missing':
                    colors.append('orange')
                else:
                    colors.append('blue')
            
            # Store figures for later saving
            figures = []
            chart_names = []
            
            # Calculate status counts (used by Chart 4 and summary message)
            status_counts = {'Faster': 0, 'On Time': 0, 'Slower': 0, 'Missing': 0}
            for data in selected_data:
                if data['tag'] == 'faster':
                    status_counts['Faster'] += 1
                elif data['tag'] == 'ontime':
                    status_counts['On Time'] += 1
                elif data['tag'] == 'missing':
                    status_counts['Missing'] += 1
                else:
                    status_counts['Slower'] += 1
            
            # Chart 1: Expected vs Actual Total Time Comparison (Bar Chart)
            if self.chart_selections['chart1_comparison']:
                fig1, ax1 = plt.subplots(figsize=(12, 6))
                figures.append(fig1)
                chart_names.append("1_comparison")
                x = range(len(elements))
                width = 0.35
                
                bars_exp = ax1.bar([i - width/2 for i in x], expected_totals, width, label='Expected', alpha=0.8, color='lightblue')
                bars_act = ax1.bar([i + width/2 for i in x], actual_totals, width, label='Actual', alpha=0.8, color='lightcoral')
                
                ax1.set_xlabel('Command', fontsize=11)
                ax1.set_ylabel('Time (seconds)', fontsize=11)
                ax1.set_title(f'Expected vs Actual Time - {sheet_name}\nProgram: {self.nc_program_name}', fontsize=12, fontweight='bold')
                # Show fewer labels if many rows
                if len(elements) > 50:
                    step = len(elements) // 20
                    ax1.set_xticks([i for i in x if i % step == 0])
                    ax1.set_xticklabels([elements[i] for i in x if i % step == 0], rotation=45, ha='right', fontsize=8)
                else:
                    ax1.set_xticks(x)
                    ax1.set_xticklabels(elements, rotation=90, ha='right', fontsize=7)
                ax1.legend(fontsize=10)
                ax1.grid(axis='y', alpha=0.3)
                
                # Add interactive cursor for Chart 1
                annot1 = ax1.annotate("", xy=(0,0), xytext=(10,10), textcoords="offset points",
                                     bbox=dict(boxstyle="round", fc="yellow", alpha=0.8),
                                     arrowprops=dict(arrowstyle="->"))
                annot1.set_visible(False)
                
                def on_hover_1(event):
                    if event.inaxes == ax1:
                        for i, (bar_e, bar_a) in enumerate(zip(bars_exp, bars_act)):
                            if bar_e.contains(event)[0]:
                                annot1.xy = (bar_e.get_x() + bar_e.get_width()/2, bar_e.get_height())
                                text = f"{elements[i]}\nExpected: {expected_totals[i]:.3f}s"
                                # Add optional fields if available
                                if selected_data[i].get('feedrate'):
                                    text += f"\nFeedRate: {selected_data[i]['feedrate']}"
                                if selected_data[i].get('sorting_address'):
                                    text += f"\nSortingAddress: {selected_data[i]['sorting_address']}"
                                if selected_data[i].get('comment'):
                                    text += f"\nComment: {selected_data[i]['comment']}"
                                annot1.set_text(text)
                                annot1.set_visible(True)
                                fig1.canvas.draw_idle()
                                return
                            elif bar_a.contains(event)[0]:
                                annot1.xy = (bar_a.get_x() + bar_a.get_width()/2, bar_a.get_height())
                                text = f"{elements[i]}\nActual: {actual_totals[i]:.3f}s"
                                # Add optional fields if available
                                if selected_data[i].get('feedrate'):
                                    text += f"\nFeedRate: {selected_data[i]['feedrate']}"
                                if selected_data[i].get('sorting_address'):
                                    text += f"\nSortingAddress: {selected_data[i]['sorting_address']}"
                                if selected_data[i].get('comment'):
                                    text += f"\nComment: {selected_data[i]['comment']}"
                                annot1.set_text(text)
                                annot1.set_visible(True)
                                fig1.canvas.draw_idle()
                                return
                        annot1.set_visible(False)
                        fig1.canvas.draw_idle()
                
                fig1.canvas.mpl_connect("motion_notify_event", on_hover_1)
                
                # Add mouse scroll zoom functionality for Chart 1
                def on_scroll_1(event):
                    if event.inaxes == ax1:
                        cur_xlim = ax1.get_xlim()
                        cur_ylim = ax1.get_ylim()
                        xdata = event.xdata if event.xdata is not None else (cur_xlim[0] + cur_xlim[1]) / 2
                        ydata = event.ydata if event.ydata is not None else (cur_ylim[0] + cur_ylim[1]) / 2
                        zoom_factor = 0.9 if event.button == 'up' else 1.1
                        new_xlim = [xdata - (xdata - cur_xlim[0]) * zoom_factor,
                                   xdata + (cur_xlim[1] - xdata) * zoom_factor]
                        new_ylim = [ydata - (ydata - cur_ylim[0]) * zoom_factor,
                                   ydata + (cur_ylim[1] - ydata) * zoom_factor]
                        ax1.set_xlim(new_xlim)
                        ax1.set_ylim(new_ylim)
                        fig1.canvas.draw_idle()
                
                fig1.canvas.mpl_connect("scroll_event", on_scroll_1)
                plt.tight_layout()
            
            # Chart 2: Difference from Expected (Bar Chart with colors)
            if self.chart_selections['chart2_difference']:
                fig2, ax2 = plt.subplots(figsize=(12, 6))
                figures.append(fig2)
                chart_names.append("2_difference")
                x = range(len(elements))
                bars2 = ax2.bar(x, differences, color=colors, alpha=0.7)
                ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
                ax2.set_xlabel('Command', fontsize=11)
                ax2.set_ylabel('Time Difference (seconds)', fontsize=11)
                ax2.set_title(f'Time Difference from Expected - {sheet_name}\nProgram: {self.nc_program_name}', fontsize=12, fontweight='bold')
                # Show fewer labels if many rows
                if len(elements) > 50:
                    step = len(elements) // 20
                    ax2.set_xticks([i for i in x if i % step == 0])
                    ax2.set_xticklabels([elements[i] for i in x if i % step == 0], rotation=45, ha='right', fontsize=8)
                else:
                    ax2.set_xticks(x)
                    ax2.set_xticklabels(elements, rotation=90, ha='right', fontsize=7)
                ax2.grid(axis='y', alpha=0.3)
                
                # Add legend for colors
                legend_elements = [Patch(facecolor='green', alpha=0.7, label='Faster'),
                                 Patch(facecolor='blue', alpha=0.7, label='On Time'),
                                 Patch(facecolor='orange', alpha=0.7, label='Missing'),
                                 Patch(facecolor='red', alpha=0.7, label='Slower')]
                ax2.legend(handles=legend_elements, fontsize=10)
                
                # Add interactive cursor for Chart 2
                annot2 = ax2.annotate("", xy=(0,0), xytext=(10,10), textcoords="offset points",
                                     bbox=dict(boxstyle="round", fc="yellow", alpha=0.8),
                                     arrowprops=dict(arrowstyle="->"))
                annot2.set_visible(False)
                
                def on_hover_2(event):
                    if event.inaxes == ax2:
                        for i, bar in enumerate(bars2):
                            if bar.contains(event)[0]:
                                annot2.xy = (bar.get_x() + bar.get_width()/2, bar.get_height())
                                text = f"{elements[i]}\nDiff: {differences[i]:+.3f}s\nDiff %: {diff_percentages[i]:+.1f}%"
                                # Add optional fields if available
                                if selected_data[i].get('feedrate'):
                                    text += f"\nFeedRate: {selected_data[i]['feedrate']}"
                                if selected_data[i].get('sorting_address'):
                                    text += f"\nSortingAddress: {selected_data[i]['sorting_address']}"
                                if selected_data[i].get('comment'):
                                    text += f"\nComment: {selected_data[i]['comment']}"
                                annot2.set_text(text)
                                annot2.set_visible(True)
                                fig2.canvas.draw_idle()
                                return
                        annot2.set_visible(False)
                        fig2.canvas.draw_idle()
                
                fig2.canvas.mpl_connect("motion_notify_event", on_hover_2)
                
                # Add mouse scroll zoom functionality for Chart 2
                def on_scroll_2(event):
                    if event.inaxes == ax2:
                        cur_xlim = ax2.get_xlim()
                        cur_ylim = ax2.get_ylim()
                        xdata = event.xdata if event.xdata is not None else (cur_xlim[0] + cur_xlim[1]) / 2
                        ydata = event.ydata if event.ydata is not None else (cur_ylim[0] + cur_ylim[1]) / 2
                        zoom_factor = 0.9 if event.button == 'up' else 1.1
                        new_xlim = [xdata - (xdata - cur_xlim[0]) * zoom_factor,
                                   xdata + (cur_xlim[1] - xdata) * zoom_factor]
                        new_ylim = [ydata - (ydata - cur_ylim[0]) * zoom_factor,
                                   ydata + (cur_ylim[1] - ydata) * zoom_factor]
                        ax2.set_xlim(new_xlim)
                        ax2.set_ylim(new_ylim)
                        fig2.canvas.draw_idle()
                
                fig2.canvas.mpl_connect("scroll_event", on_scroll_2)
                plt.tight_layout()
            
            # Chart 3: Percentage Difference (Line Chart)
            if self.chart_selections['chart3_percentage']:
                fig3, ax3 = plt.subplots(figsize=(12, 6))
                figures.append(fig3)
                chart_names.append("3_percentage")
                x = range(len(elements))
                line3 = ax3.plot(x, diff_percentages, marker='o', linewidth=1, markersize=4, color='navy', label='Diff %')[0]
                ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
                
                # Add tolerance lines
                tolerance = self.tolerance_var.get()
                ax3.axhline(y=tolerance, color='blue', linestyle='--', linewidth=1, alpha=0.5, label=f'±{tolerance}% tolerance')
                ax3.axhline(y=-tolerance, color='blue', linestyle='--', linewidth=1, alpha=0.5)
                
                ax3.set_xlabel('Command', fontsize=11)
                ax3.set_ylabel('Difference (%)', fontsize=11)
                ax3.set_title(f'Percentage Difference from Expected - {sheet_name}\nProgram: {self.nc_program_name}', fontsize=12, fontweight='bold')
                # Show fewer labels if many rows
                if len(elements) > 50:
                    step = len(elements) // 20
                    ax3.set_xticks([i for i in x if i % step == 0])
                    ax3.set_xticklabels([elements[i] for i in x if i % step == 0], rotation=45, ha='right', fontsize=8)
                else:
                    ax3.set_xticks(x)
                    ax3.set_xticklabels(elements, rotation=90, ha='right', fontsize=7)
                ax3.grid(True, alpha=0.3)
                ax3.legend(fontsize=10)
                
                # Add interactive cursor for Chart 3
                annot3 = ax3.annotate("", xy=(0,0), xytext=(10,10), textcoords="offset points",
                                     bbox=dict(boxstyle="round", fc="yellow", alpha=0.8),
                                     arrowprops=dict(arrowstyle="->"))
                annot3.set_visible(False)
                
                def on_hover_3(event):
                    if event.inaxes == ax3:
                        cont, ind = line3.contains(event)
                        if cont:
                            idx = ind["ind"][0]
                            annot3.xy = (idx, diff_percentages[idx])
                            text = f"{elements[idx]}\nDiff %: {diff_percentages[idx]:+.1f}%"
                            # Add optional fields if available
                            if selected_data[idx].get('feedrate'):
                                text += f"\nFeedRate: {selected_data[idx]['feedrate']}"
                            if selected_data[idx].get('sorting_address'):
                                text += f"\nSortingAddress: {selected_data[idx]['sorting_address']}"
                            if selected_data[idx].get('comment'):
                                text += f"\nComment: {selected_data[idx]['comment']}"
                            annot3.set_text(text)
                            annot3.set_visible(True)
                            fig3.canvas.draw_idle()
                        else:
                            annot3.set_visible(False)
                            fig3.canvas.draw_idle()
                
                fig3.canvas.mpl_connect("motion_notify_event", on_hover_3)
                
                # Add mouse scroll zoom functionality for Chart 3
                def on_scroll_3(event):
                    if event.inaxes == ax3:
                        cur_xlim = ax3.get_xlim()
                        cur_ylim = ax3.get_ylim()
                        xdata = event.xdata if event.xdata is not None else (cur_xlim[0] + cur_xlim[1]) / 2
                        ydata = event.ydata if event.ydata is not None else (cur_ylim[0] + cur_ylim[1]) / 2
                        zoom_factor = 0.9 if event.button == 'up' else 1.1
                        new_xlim = [xdata - (xdata - cur_xlim[0]) * zoom_factor,
                                   xdata + (cur_xlim[1] - xdata) * zoom_factor]
                        new_ylim = [ydata - (ydata - cur_ylim[0]) * zoom_factor,
                                   ydata + (cur_ylim[1] - ydata) * zoom_factor]
                        ax3.set_xlim(new_xlim)
                        ax3.set_ylim(new_ylim)
                        fig3.canvas.draw_idle()
                
                fig3.canvas.mpl_connect("scroll_event", on_scroll_3)
                plt.tight_layout()
            
            # Chart 4: Status Distribution (Pie Chart)
            if self.chart_selections['chart4_status']:
                fig4, ax4 = plt.subplots(figsize=(8, 8))
                figures.append(fig4)
                chart_names.append("4_status")
                
                # Remove zero counts for cleaner pie chart (work on a copy)
                pie_status_counts = {k: v for k, v in status_counts.items() if v > 0}
                pie_colors = {'Faster': 'green', 'On Time': 'blue', 'Slower': 'red', 'Missing': 'orange'}
                colors_list = [pie_colors[k] for k in pie_status_counts.keys()]
                pie_labels  = [f"{k}\n({v})" for k, v in pie_status_counts.items()]
                wedges, texts, autotexts = ax4.pie(pie_status_counts.values(), labels=pie_labels, colors=colors_list, 
                       autopct='%1.1f%%', startangle=90, textprops={'fontsize': 11})
                ax4.set_title(f'Status Distribution - {sheet_name}\nProgram: {self.nc_program_name}\nTotal Rows: {len(selected_data)}', 
                             fontsize=12, fontweight='bold')
                plt.tight_layout()
            
            # Chart 5: Cumulative Timeline - Expected vs Actual time progression
            if self.chart_selections['chart6_cumulative']:
                fig5, ax5 = plt.subplots(figsize=(14, 6))
                figures.append(fig5)
                chart_names.append("5_cumulative")
                
                # Build cumulative data for selected rows
                cumulative_expected = []
                cumulative_actual = []
                row_labels = []
                cum_exp = 0
                cum_act = 0
                
                for data in selected_data:
                    cum_exp += data['expected_time']
                    cum_act += data['actual_time']
                    cumulative_expected.append(cum_exp)
                    cumulative_actual.append(cum_act)
                    row_labels.append(data['element'])
                
                # Plot cumulative timeline
                x_positions = range(len(row_labels))
                line_exp = ax5.plot(x_positions, cumulative_expected, 'b-o', linewidth=1, markersize=5, 
                        label='Expected (Cumulative)', alpha=0.8)[0]
                line_act = ax5.plot(x_positions, cumulative_actual, 'r-o', linewidth=1, markersize=5, 
                        label='Actual (Cumulative)', alpha=0.8)[0]
                
                # Fill area between lines to show difference
                ax5.fill_between(x_positions, cumulative_expected, cumulative_actual, 
                                alpha=0.2, color='gray', label='Difference')
                
                # Add secondary y-axis for percentage difference
                ax5_secondary = ax5.twinx()
                
                # Calculate cumulative percentage difference at each point
                cumulative_diff_pct = []
                for exp, act in zip(cumulative_expected, cumulative_actual):
                    if exp > 0:
                        pct = ((act - exp) / exp * 100)
                        cumulative_diff_pct.append(pct)
                    else:
                        cumulative_diff_pct.append(0)
                
                # Plot percentage difference on secondary axis
                line_pct = ax5_secondary.plot(x_positions, cumulative_diff_pct, 'g--', linewidth=1.5, 
                                              marker='s', markersize=4, label='Cumulative Diff %', alpha=0.7)[0]
                
                # Add tolerance reference lines on secondary axis
                tolerance = self.tolerance_var.get()
                ax5_secondary.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
                ax5_secondary.axhline(y=tolerance, color='orange', linestyle=':', linewidth=1, alpha=0.5)
                ax5_secondary.axhline(y=-tolerance, color='orange', linestyle=':', linewidth=1, alpha=0.5)
                
                ax5.set_xlabel('Command', fontsize=11)
                ax5.set_ylabel('Cumulative Time (seconds)', fontsize=11, color='navy')
                ax5_secondary.set_ylabel('Cumulative Difference (%)', fontsize=11, color='green')
                ax5_secondary.tick_params(axis='y', labelcolor='green')
                ax5.tick_params(axis='y', labelcolor='navy')
                
                ax5.set_title(f'Cumulative Time Progress - Expected vs Actual - {sheet_name}\nProgram: {self.nc_program_name}', 
                             fontsize=12, fontweight='bold')
                
                # Combine legends from both axes
                lines1, labels1 = ax5.get_legend_handles_labels()
                lines2, labels2 = ax5_secondary.get_legend_handles_labels()
                ax5.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)
                
                ax5.grid(True, alpha=0.3)
                
                # Set x-axis labels - show command names
                if len(row_labels) <= 20:
                    ax5.set_xticks(x_positions)
                    ax5.set_xticklabels(row_labels, rotation=45, ha='right', fontsize=8)
                elif len(row_labels) <= 50:
                    step = 2
                    ax5.set_xticks(x_positions[::step])
                    ax5.set_xticklabels(row_labels[::step], rotation=45, ha='right', fontsize=8)
                else:
                    step = max(1, len(row_labels) // 20)
                    ax5.set_xticks(x_positions[::step])
                    ax5.set_xticklabels(row_labels[::step], rotation=45, ha='right', fontsize=8)
                
                # Add final time annotations
                if cumulative_expected and cumulative_actual:
                    final_diff_pct = cumulative_diff_pct[-1] if cumulative_diff_pct else 0
                    ax5.annotate(f'Expected: {cumulative_expected[-1]:.2f}s', 
                               xy=(len(row_labels)-1, cumulative_expected[-1]), 
                               xytext=(10, -10), textcoords='offset points',
                               fontsize=10, color='blue', fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.7))
                    ax5.annotate(f'Actual: {cumulative_actual[-1]:.2f}s\nDiff: {final_diff_pct:+.1f}%', 
                               xy=(len(row_labels)-1, cumulative_actual[-1]), 
                               xytext=(10, 10), textcoords='offset points',
                               fontsize=10, color='red', fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='lightcoral', alpha=0.7))
                
                # Add interactive cursor for Chart 5
                annot5 = ax5.annotate("", xy=(0,0), xytext=(10,10), textcoords="offset points",
                                     bbox=dict(boxstyle="round", fc="yellow", alpha=0.8),
                                     arrowprops=dict(arrowstyle="->"))
                annot5.set_visible(False)
                
                def on_hover_5(event):
                    if event.inaxes == ax5 or event.inaxes == ax5_secondary:
                        cont_exp, ind_exp = line_exp.contains(event)
                        cont_act, ind_act = line_act.contains(event)
                        cont_pct, ind_pct = line_pct.contains(event)
                        
                        if cont_exp:
                            idx = ind_exp["ind"][0]
                            annot5.xy = (idx, cumulative_expected[idx])
                            text = f"{row_labels[idx]}\nExpected Cumulative: {cumulative_expected[idx]:.3f}s\nDiff: {cumulative_diff_pct[idx]:+.1f}%"
                            # Add optional fields if available
                            if selected_data[idx].get('feedrate'):
                                text += f"\nFeedRate: {selected_data[idx]['feedrate']}"
                            if selected_data[idx].get('sorting_address'):
                                text += f"\nSortingAddress: {selected_data[idx]['sorting_address']}"
                            if selected_data[idx].get('comment'):
                                text += f"\nComment: {selected_data[idx]['comment']}"
                            annot5.set_text(text)
                            annot5.set_visible(True)
                            fig5.canvas.draw_idle()
                        elif cont_act:
                            idx = ind_act["ind"][0]
                            annot5.xy = (idx, cumulative_actual[idx])
                            text = f"{row_labels[idx]}\nActual Cumulative: {cumulative_actual[idx]:.3f}s\nDiff: {cumulative_diff_pct[idx]:+.1f}%"
                            # Add optional fields if available
                            if selected_data[idx].get('feedrate'):
                                text += f"\nFeedRate: {selected_data[idx]['feedrate']}"
                            if selected_data[idx].get('sorting_address'):
                                text += f"\nSortingAddress: {selected_data[idx]['sorting_address']}"
                            if selected_data[idx].get('comment'):
                                text += f"\nComment: {selected_data[idx]['comment']}"
                            annot5.set_text(text)
                            annot5.set_visible(True)
                            fig5.canvas.draw_idle()
                        elif cont_pct:
                            idx = ind_pct["ind"][0]
                            # Position annotation on secondary axis
                            annot5.xy = (idx, cumulative_expected[idx])
                            text = f"{row_labels[idx]}\nCumulative Diff %: {cumulative_diff_pct[idx]:+.1f}%\nExpected: {cumulative_expected[idx]:.3f}s\nActual: {cumulative_actual[idx]:.3f}s"
                            # Add optional fields if available
                            if selected_data[idx].get('feedrate'):
                                text += f"\nFeedRate: {selected_data[idx]['feedrate']}"
                            if selected_data[idx].get('sorting_address'):
                                text += f"\nSortingAddress: {selected_data[idx]['sorting_address']}"
                            if selected_data[idx].get('comment'):
                                text += f"\nComment: {selected_data[idx]['comment']}"
                            annot5.set_text(text)
                            annot5.set_visible(True)
                            fig5.canvas.draw_idle()
                        else:
                            annot5.set_visible(False)
                            fig5.canvas.draw_idle()
                
                fig5.canvas.mpl_connect("motion_notify_event", on_hover_5)
                
                # Add mouse scroll zoom functionality for Chart 5
                def on_scroll_5(event):
                    if event.inaxes in [ax5, ax5_secondary]:
                        # Get current axis limits
                        cur_xlim = ax5.get_xlim()
                        cur_ylim = ax5.get_ylim()
                        cur_ylim_secondary = ax5_secondary.get_ylim()
                        
                        # Get event location
                        xdata = event.xdata if event.xdata is not None else (cur_xlim[0] + cur_xlim[1]) / 2
                        ydata = event.ydata if event.ydata is not None else (cur_ylim[0] + cur_ylim[1]) / 2
                        
                        # Set zoom factor
                        zoom_factor = 0.9 if event.button == 'up' else 1.1
                        
                        # Calculate new limits for x-axis
                        x_range = (cur_xlim[1] - cur_xlim[0]) * zoom_factor
                        x_center = xdata
                        new_xlim = [x_center - (x_center - cur_xlim[0]) * zoom_factor,
                                   x_center + (cur_xlim[1] - x_center) * zoom_factor]
                        
                        # Calculate new limits for primary y-axis
                        y_range = (cur_ylim[1] - cur_ylim[0]) * zoom_factor
                        y_center = ydata if event.inaxes == ax5 else (cur_ylim[0] + cur_ylim[1]) / 2
                        new_ylim = [y_center - (y_center - cur_ylim[0]) * zoom_factor,
                                   y_center + (cur_ylim[1] - y_center) * zoom_factor]
                        
                        # Calculate new limits for secondary y-axis
                        y_range_secondary = (cur_ylim_secondary[1] - cur_ylim_secondary[0]) * zoom_factor
                        y_center_secondary = event.ydata if event.inaxes == ax5_secondary else (cur_ylim_secondary[0] + cur_ylim_secondary[1]) / 2
                        new_ylim_secondary = [y_center_secondary - (y_center_secondary - cur_ylim_secondary[0]) * zoom_factor,
                                             y_center_secondary + (cur_ylim_secondary[1] - y_center_secondary) * zoom_factor]
                        
                        # Set new limits
                        ax5.set_xlim(new_xlim)
                        ax5.set_ylim(new_ylim)
                        ax5_secondary.set_ylim(new_ylim_secondary)
                        
                        # Redraw canvas
                        fig5.canvas.draw_idle()
                
                fig5.canvas.mpl_connect("scroll_event", on_scroll_5)
                plt.tight_layout()
            
            # Chart 6: Waterfall Chart - Shows contribution to cumulative difference
            if self.chart_selections['chart7_waterfall']:
                fig6, ax6 = plt.subplots(figsize=(14, 6))
                figures.append(fig6)
                chart_names.append("6_waterfall")
                fig7, ax7 = plt.subplots(figsize=(14, 7))
                figures.append(fig7)
                chart_names.append("7_waterfall")
                
                # Calculate individual differences for waterfall
                waterfall_values = []
                waterfall_colors = []
                cumulative_for_waterfall = 0
                
                for data in selected_data:
                    diff = data['diff']
                    waterfall_values.append(diff)
                    # Color based on whether it adds or subtracts time
                    if diff > 0:
                        waterfall_colors.append('red')
                    elif diff < 0:
                        waterfall_colors.append('green')
                    else:
                        waterfall_colors.append('gray')
                
                # Create waterfall effect with bars
                x_pos = range(len(elements))
                bottom_positions = []
                cumulative = 0
                
                for i, val in enumerate(waterfall_values):
                    bottom_positions.append(cumulative)
                    cumulative += val
                
                # Plot bars
                bars6 = ax6.bar(x_pos, waterfall_values, bottom=bottom_positions, 
                               color=waterfall_colors, alpha=0.7, edgecolor='black', linewidth=0.5)
                
                # Draw connecting lines between bars
                for i in range(len(x_pos) - 1):
                    ax6.plot([i + 0.4, i + 0.6], 
                            [bottom_positions[i] + waterfall_values[i], 
                             bottom_positions[i+1]], 
                            'k--', linewidth=0.8, alpha=0.5)
                
                # Add horizontal line at zero
                ax6.axhline(y=0, color='black', linestyle='-', linewidth=1)
                
                # Add final cumulative bar
                final_cumulative = sum(waterfall_values)
                ax6.bar(len(x_pos), final_cumulative, color='blue', alpha=0.3, 
                       edgecolor='blue', linewidth=2, width=0.8, label=f'Total Diff: {final_cumulative:+.3f}s')
                
                ax6.set_xlabel('Command', fontsize=11)
                ax6.set_ylabel('Time Difference Contribution (seconds)', fontsize=11)
                ax6.set_title(f'Waterfall Chart - Cumulative Difference Breakdown - {sheet_name}\nProgram: {self.nc_program_name}', 
                             fontsize=12, fontweight='bold')
                ax6.legend(fontsize=10)
                ax6.grid(axis='y', alpha=0.3)
                
                # Set x-axis labels
                if len(elements) > 50:
                    step = len(elements) // 20
                    ax6.set_xticks([i for i in x_pos if i % step == 0] + [len(x_pos)])
                    labels = [elements[i] for i in x_pos if i % step == 0] + ['TOTAL']
                    ax6.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
                else:
                    ax6.set_xticks(list(x_pos) + [len(x_pos)])
                    ax6.set_xticklabels(elements + ['TOTAL'], rotation=90, ha='right', fontsize=7)
                
                # Add interactive cursor for Chart 6
                annot6 = ax6.annotate("", xy=(0,0), xytext=(10,10), textcoords="offset points",
                                     bbox=dict(boxstyle="round", fc="yellow", alpha=0.8),
                                     arrowprops=dict(arrowstyle="->"))
                annot6.set_visible(False)
                
                def on_hover_6(event):
                    if event.inaxes == ax6:
                        for i, bar in enumerate(bars6):
                            if bar.contains(event)[0]:
                                annot6.xy = (bar.get_x() + bar.get_width()/2, 
                                            bottom_positions[i] + waterfall_values[i]/2)
                                text = f"{elements[i]}\nDiff: {waterfall_values[i]:+.3f}s\nCumulative: {bottom_positions[i] + waterfall_values[i]:.3f}s"
                                # Add optional fields if available
                                if selected_data[i].get('feedrate'):
                                    text += f"\nFeedRate: {selected_data[i]['feedrate']}"
                                if selected_data[i].get('sorting_address'):
                                    text += f"\nSortingAddress: {selected_data[i]['sorting_address']}"
                                if selected_data[i].get('comment'):
                                    text += f"\nComment: {selected_data[i]['comment']}"
                                annot6.set_text(text)
                                annot6.set_visible(True)
                                fig6.canvas.draw_idle()
                                return
                        annot6.set_visible(False)
                        fig6.canvas.draw_idle()
                
                fig6.canvas.mpl_connect("motion_notify_event", on_hover_6)
                
                # Add mouse scroll zoom functionality for Chart 6
                def on_scroll_6(event):
                    if event.inaxes == ax6:
                        cur_xlim = ax6.get_xlim()
                        cur_ylim = ax6.get_ylim()
                        xdata = event.xdata if event.xdata is not None else (cur_xlim[0] + cur_xlim[1]) / 2
                        ydata = event.ydata if event.ydata is not None else (cur_ylim[0] + cur_ylim[1]) / 2
                        zoom_factor = 0.9 if event.button == 'up' else 1.1
                        new_xlim = [xdata - (xdata - cur_xlim[0]) * zoom_factor,
                                   xdata + (cur_xlim[1] - xdata) * zoom_factor]
                        new_ylim = [ydata - (ydata - cur_ylim[0]) * zoom_factor,
                                   ydata + (cur_ylim[1] - ydata) * zoom_factor]
                        ax6.set_xlim(new_xlim)
                        ax6.set_ylim(new_ylim)
                        fig6.canvas.draw_idle()
                
                fig6.canvas.mpl_connect("scroll_event", on_scroll_6)
                plt.tight_layout()
            
            # Chart 7: Synchronized Dual Timeline with Difference Bars
            if self.chart_selections['chart8_dual_timeline']:
                fig7, ax7 = plt.subplots(figsize=(14, 8))
                figures.append(fig7)
                chart_names.append("7_dual_timeline")
                
                # Build time positions for both timelines
                expected_positions = []
                actual_positions = []
                exp_cum = 0
                act_cum = 0
                
                for data in selected_data:
                    expected_positions.append((exp_cum, exp_cum + data['expected_time']))
                    actual_positions.append((act_cum, act_cum + data['actual_time']))
                    exp_cum += data['expected_time']
                    act_cum += data['actual_time']
                
                # Plot expected timeline (top)
                y_expected = 2
                for i, (start, end) in enumerate(expected_positions):
                    # Color based on status
                    if selected_data[i]['tag'] == 'faster':
                        color = 'lightgreen'
                    elif selected_data[i]['tag'] == 'slower':
                        color = 'lightcoral'
                    elif selected_data[i]['tag'] == 'missing':
                        color = 'orange'
                    else:
                        color = 'lightblue'
                    
                    ax7.barh(y_expected, end - start, left=start, height=0.6, 
                            color=color, edgecolor='black', linewidth=0.5, alpha=0.8)
                    
                    # Add command name if bar is wide enough
                    if (end - start) > (exp_cum / 30):  # Show label if bar > ~3% of total
                        ax7.text((start + end) / 2, y_expected, elements[i], 
                                ha='center', va='center', fontsize=7, rotation=0)
                
                # Plot actual timeline (bottom)
                y_actual = 1
                for i, (start, end) in enumerate(actual_positions):
                    # Color based on status
                    if selected_data[i]['tag'] == 'faster':
                        color = 'lightgreen'
                    elif selected_data[i]['tag'] == 'slower':
                        color = 'lightcoral'
                    elif selected_data[i]['tag'] == 'missing':
                        color = 'orange'
                    else:
                        color = 'lightblue'
                    
                    ax7.barh(y_actual, end - start, left=start, height=0.6, 
                            color=color, edgecolor='black', linewidth=0.5, alpha=0.8)
                    
                    # Add command name if bar is wide enough
                    if (end - start) > (act_cum / 30):
                        ax7.text((start + end) / 2, y_actual, elements[i], 
                                ha='center', va='center', fontsize=7, rotation=0)
                
                # Draw difference bars between timelines
                for i in range(len(selected_data)):
                    exp_mid = (expected_positions[i][0] + expected_positions[i][1]) / 2
                    act_mid = (actual_positions[i][0] + actual_positions[i][1]) / 2
                    
                    # Determine color based on difference direction
                    if selected_data[i]['diff'] > 0:
                        line_color = 'red'
                        line_style = '-'
                    elif selected_data[i]['diff'] < 0:
                        line_color = 'green'
                        line_style = '-'
                    else:
                        line_color = 'gray'
                        line_style = ':'
                    
                    # Draw vertical line showing difference
                    ax7.plot([act_mid, exp_mid], [y_actual + 0.3, y_expected - 0.3], 
                            color=line_color, linestyle=line_style, linewidth=1.5, alpha=0.6)
                    
                    # Add difference value for significant differences
                    if abs(selected_data[i]['diff']) > 0.1:  # Show if difference > 0.1s
                        mid_y = (y_actual + y_expected) / 2
                        ax7.text((act_mid + exp_mid) / 2, mid_y, f"{selected_data[i]['diff']:+.2f}s", 
                                ha='center', va='center', fontsize=6, 
                                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))
                
                # Add timeline end markers
                ax7.axvline(x=exp_cum, color='blue', linestyle='--', linewidth=1.5, alpha=0.7, 
                           label=f'Expected End: {exp_cum:.2f}s')
                ax7.axvline(x=act_cum, color='red', linestyle='--', linewidth=1.5, alpha=0.7, 
                           label=f'Actual End: {act_cum:.2f}s')
                
                ax7.set_yticks([y_actual, y_expected])
                ax7.set_yticklabels(['Actual Timeline', 'Expected Timeline'], fontsize=11)
                ax7.set_xlabel('Time (seconds)', fontsize=11)
                ax7.set_title(f'Synchronized Dual Timeline - Difference Visualization - {sheet_name}\nProgram: {self.nc_program_name}\nVertical lines show time difference at each command', 
                             fontsize=12, fontweight='bold')
                ax7.legend(loc='upper right', fontsize=10)
                ax7.grid(axis='x', alpha=0.3)
                ax7.set_ylim(0.5, 2.8)
                
                # Add color legend
                legend_elements = [
                    Patch(facecolor='lightgreen', edgecolor='black', label='Faster'),
                    Patch(facecolor='lightblue', edgecolor='black', label='On Time'),
                    Patch(facecolor='lightcoral', edgecolor='black', label='Slower'),
                    Patch(facecolor='orange', edgecolor='black', label='Missing')
                ]
                ax7.legend(handles=legend_elements, loc='upper left', fontsize=9, ncol=4)
                
                # Add mouse scroll zoom functionality for Chart 7
                def on_scroll_7(event):
                    if event.inaxes == ax7:
                        cur_xlim = ax7.get_xlim()
                        cur_ylim = ax7.get_ylim()
                        xdata = event.xdata if event.xdata is not None else (cur_xlim[0] + cur_xlim[1]) / 2
                        ydata = event.ydata if event.ydata is not None else (cur_ylim[0] + cur_ylim[1]) / 2
                        zoom_factor = 0.9 if event.button == 'up' else 1.1
                        new_xlim = [xdata - (xdata - cur_xlim[0]) * zoom_factor,
                                   xdata + (cur_xlim[1] - xdata) * zoom_factor]
                        new_ylim = [ydata - (ydata - cur_ylim[0]) * zoom_factor,
                                   ydata + (cur_ylim[1] - ydata) * zoom_factor]
                        ax7.set_xlim(new_xlim)
                        ax7.set_ylim(new_ylim)
                        fig7.canvas.draw_idle()
                
                fig7.canvas.mpl_connect("scroll_event", on_scroll_7)
                plt.tight_layout()
            
            # Save all figures and show them
            import re
            safe_sheet_name = re.sub(r'[<>:"/\\|?*]', '_', sheet_name)
            safe_sheet_name = safe_sheet_name.replace(' ', '_')
            base_filename = f"{os.path.splitext(os.path.basename(self.xml_file))[0]}_{safe_sheet_name}"
            output_dir = os.path.dirname(self.xml_file)
            
            saved_files = []
            for fig, name in zip(figures, chart_names):
                output_path = os.path.join(output_dir, f"{base_filename}_{name}.png")
                fig.savefig(output_path, dpi=150, bbox_inches='tight')
                saved_files.append(output_path)
            
            # Show all plots
            plt.show(block=False)
            
            # Calculate stats
            selected_expected_total = sum(d['expected_time'] for d in selected_data)
            selected_actual_total = sum(d['actual_time'] for d in selected_data)
            
            # Build chart list description
            chart_descriptions = {
                '1_comparison': '1. Expected vs Actual Time Comparison',
                '2_difference': '2. Time Difference from Expected',
                '3_percentage': '3. Percentage Difference',
                '4_status': '4. Status Distribution (Pie Chart)',
                '5_cumulative': '5. Cumulative Time Progress',
                '6_waterfall': '6. Waterfall Chart (Difference Breakdown)',
                '7_dual_timeline': '7. Synchronized Dual Timeline'
            }
            created_charts = '\n'.join([chart_descriptions[name] for name in chart_names if name in chart_descriptions])
            
            messagebox.showinfo("Visualization Created", 
                              f"{len(figures)} interactive chart(s) created!\n\n"
                              f"Selected Rows: {len(selected_data)}\n"
                              f"Expected Total: {selected_expected_total:.3f}s\n"
                              f"Actual Total: {selected_actual_total:.3f}s\n\n"
                              f"Faster: {status_counts.get('Faster', 0)}, "
                              f"On Time: {status_counts.get('On Time', 0)}, "
                              f"Slower: {status_counts.get('Slower', 0)}, "
                              f"Missing: {status_counts.get('Missing', 0)}\n\n"
                              f"Charts Created:\n"
                              f"{created_charts}\n\n"
                              f"Files saved to:\n{output_dir}\n\n"
                              f"Features:\n"
                              f"• Zoom: Use toolbar or scroll wheel\n"
                              f"• Pan: Click and drag\n"
                              f"• Hover over data points for details\n"
                              f"• Each chart in separate window")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messagebox.showerror("Visualization Failed", 
                               f"Failed to create visualization:\n{str(e)}\n\n"
                               f"Details:\n{error_details[:500]}")


def main():
    root = tk.Tk()
    app = SheetTimesComparisonUI(root)
    
    # Load file from command line if provided
    import sys
    if len(sys.argv) > 1:
        root.after(100, lambda: app.load_xml_file(sys.argv[1]))
    
    root.mainloop()


if __name__ == "__main__":
    main()
