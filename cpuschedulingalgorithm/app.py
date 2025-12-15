# app.py

from flask import Flask, render_template, request, jsonify
# Import all scheduling functions and metrics calculator
from scheduler import (
    Process, solve_fcfs, solve_round_robin, solve_sjf, solve_srtf, 
    solve_priority, solve_priority_preemptive, calculate_metrics
) 

app = Flask(__name__)

# --- The Homepage Route ---
@app.route('/')
def index():
    # Trigger image of the simulator's main function
    return render_template('index.html')

# --- The Central Calculation Route (Runs ONE algorithm) ---
@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    
    # 1. Get ALL parameters
    algorithm = data.get('algorithm', 'fcfs')
    
    # VITAL SAFETY CHECK 1: Safely convert quantum to int
    try:
        quantum = int(data.get('quantum', 2)) 
    except ValueError:
        return jsonify(error="Invalid value for Time Quantum. Must be an integer."), 400

    # 2. Convert raw data into Process objects 
    processes = []
    for i, p_data in enumerate(data['processes']):
        # p_data is expected to be [pid_string, at_value, bt_value, pr_value]
        pid = f"P{i+1}"
        try:
            at = int(p_data[1])
            bt = int(p_data[2])
            # Handle empty or None priority value
            pr = int(p_data[3]) if len(p_data) > 3 and p_data[3] else None
            processes.append(Process(pid, at, bt, pr))
        except (ValueError, IndexError) as e:
            # If any input is invalid (e.g., text instead of number)
            print(f"Error parsing process data: {e}")
            return jsonify(error="Invalid process input (AT, BT, or Priority). Check that all values are numbers."), 400
    
    # 3. Call the correct algorithm solver
    scheduled_processes = []
    gantt_timeline = []
    
    try:
        if algorithm in ['fcfs', 'sjf', 'priority']:
            # Non-preemptive algorithms only return the scheduled list
            if algorithm == 'fcfs':
                scheduled_processes = solve_fcfs(processes)
            elif algorithm == 'sjf':
                scheduled_processes = solve_sjf(processes)
            elif algorithm == 'priority':
                scheduled_processes = solve_priority(processes)
            
            # Create dummy timeline for non-preemptive metrics
            # Start Time = CT - BT - WT. This relies on the solver correctly calculating these metrics.
            gantt_timeline = [{'pid': p.pid, 'start': p.ct - p.bt - p.wt, 'end': p.ct} for p in scheduled_processes]

        elif algorithm == 'rr':
            scheduled_processes, gantt_timeline = solve_round_robin(processes, quantum) 
            
        elif algorithm == 'srtf':
            scheduled_processes, gantt_timeline = solve_srtf(processes)

        elif algorithm == 'priority_preemptive':
            scheduled_processes, gantt_timeline = solve_priority_preemptive(processes)
            
        else:
            return jsonify(error=f"Algorithm '{algorithm}' not supported."), 400
            
    except Exception as e:
        # Catch any errors from the scheduling functions (e.g., math error, list index out of bounds)
        print(f"Error during calculation for {algorithm}: {e}")
        return jsonify(error=f"Calculation Failed: {e}"), 500
    
    # 4. Calculate Final Metrics (WT, TAT, TEI, etc.)
    final_metrics = calculate_metrics(scheduled_processes, gantt_timeline)
    
    # 5. Prepare the results for the Frontend
    results = [p.to_dict() for p in scheduled_processes]
    
    # 6. Send the JSON data back
    return jsonify(
        results=results, 
        gantt_timeline=gantt_timeline,
        metrics=final_metrics
    )

# --- The Comparison Route (Runs MULTIPLE algorithms) ---
@app.route('/compare', methods=['POST'])
def compare():
    data = request.json
    processes_data = data['processes']
    
    # VITAL SAFETY CHECK 2: Safely convert quantum to int
    try:
        quantum = int(data.get('quantum', 2))
    except ValueError:
        return jsonify(error="Invalid value for Time Quantum in comparison. Must be an integer."), 400
    
    comparison_results = []
    
    # 1. Define the algorithms to compare
    ALGORITHMS_TO_COMPARE = [
        ('FCFS', solve_fcfs, False),
        ('SJF', solve_sjf, False),
        ('Round Robin', solve_round_robin, True)
    ]
    
    # Trigger image of Gantt Chart for conceptual understanding of comparison
    
    for name, solver, is_preemptive in ALGORITHMS_TO_COMPARE:
        # A. VITAL: Re-create the process objects for EACH algorithm run!
        processes = []
        for i, p_data in enumerate(processes_data):
            pid = f"P{i+1}"
            try:
                at = int(p_data[1])
                bt = int(p_data[2])
                pr = int(p_data[3]) if len(p_data) > 3 and p_data[3] else None
                processes.append(Process(pid, at, bt, pr))
            except (ValueError, IndexError) as e:
                return jsonify(error=f"Invalid process input for {name} comparison: {e}"), 400

        # B. Run the Solver
        if is_preemptive:
            scheduled_processes, gantt_timeline = solver(processes, quantum)
        else:
            scheduled_processes = solver(processes)
            # Create timeline for non-preemptive metrics
            gantt_timeline = [{'pid': p.pid, 'start': p.ct - p.bt - p.wt, 'end': p.ct} for p in scheduled_processes]

        # C. Calculate Metrics
        metrics = calculate_metrics(scheduled_processes, gantt_timeline)
        
        # D. Store Results (VITAL SAFETY CHECK 3: Use .get() with default values)
        comparison_results.append({
            'algorithm': name,
            'avg_wt': metrics.get('avg_wt', 0.0), 
            'avg_tat': metrics.get('avg_tat', 0.0),
            'tei': metrics.get('tei', 0.0)
        })

    # 2. Return the combined results
    return jsonify(results=comparison_results)



if __name__ == '__main__':
    app.run(debug=True)