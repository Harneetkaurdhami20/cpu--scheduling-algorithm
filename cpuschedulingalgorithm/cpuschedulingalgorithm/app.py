from flask import Flask, render_template, request, jsonify
from scheduler import (
    Process, solve_fcfs, solve_round_robin, solve_sjf, solve_srtf, 
    solve_priority, solve_priority_preemptive, calculate_metrics
) 

application_server = Flask(__name__)

# --- The Homepage Route ---
@application_server.route('/')
def load_simulator_page():
    return render_template('index.html')

# --- The Central Calculation Route (Runs ONE algorithm) ---
@application_server.route('/calculate', methods=['POST'])
def run_single_algorithm():
    input_request_data = request.json
    
    algorithm_name = input_request_data.get('algorithm', 'fcfs')
    
    try:
        time_quantum_value = int(input_request_data.get('quantum', 2)) 
    except ValueError:
        return jsonify(error="Invalid value for Time Quantum. Must be an integer."), 400

    process_objects_list = []
    for process_index, process_raw_data in enumerate(input_request_data['processes']):
        process_id = f"P{process_index+1}"
        try:
            arrival_time = int(process_raw_data[1])
            burst_time = int(process_raw_data[2])
            priority_level = int(process_raw_data[3]) if len(process_raw_data) > 3 and process_raw_data[3] else None
            process_objects_list.append(Process(process_id, arrival_time, burst_time, priority_level))
        except (ValueError, IndexError) as error_detail:
            print(f"Error parsing process data: {error_detail}")
            return jsonify(error="Invalid process input (AT, BT, or Priority). Check that all values are numbers."), 400
    
    final_scheduled_jobs = []
    gantt_chart_timeline = []
    
    try:
        if algorithm_name in ['fcfs', 'sjf', 'priority']:
            if algorithm_name == 'fcfs':
                final_scheduled_jobs = solve_fcfs(process_objects_list)
            elif algorithm_name == 'sjf':
                final_scheduled_jobs = solve_sjf(process_objects_list)
            elif algorithm_name == 'priority':
                final_scheduled_jobs = solve_priority(process_objects_list)
            
            gantt_chart_timeline = [{'pid': job.pid, 'start': job.ct - job.bt - job.wt, 'end': job.ct} for job in final_scheduled_jobs]

        elif algorithm_name == 'rr':
            final_scheduled_jobs, gantt_chart_timeline = solve_round_robin(process_objects_list, time_quantum_value) 
            
        elif algorithm_name == 'srtf':
            final_scheduled_jobs, gantt_chart_timeline = solve_srtf(process_objects_list)

        elif algorithm_name == 'priority_preemptive':
            final_scheduled_jobs, gantt_chart_timeline = solve_priority_preemptive(process_objects_list)
            
        else:
            return jsonify(error=f"Algorithm '{algorithm_name}' not supported."), 400
            
    except Exception as error_detail:
        print(f"Error during calculation for {algorithm_name}: {error_detail}")
        return jsonify(error=f"Calculation Failed: {error_detail}"), 500
    
    overall_performance_metrics = calculate_metrics(final_scheduled_jobs, gantt_chart_timeline)
    
    final_results_for_table = [job.to_dict() for job in final_scheduled_jobs]
    
    return jsonify(
        results=final_results_for_table, 
        gantt_timeline=gantt_chart_timeline,
        metrics=overall_performance_metrics
    )

# --- The Comparison Route (Runs MULTIPLE algorithms) ---
@application_server.route('/compare', methods=['POST'])
def run_comparison_algorithms():
    input_request_data = request.json
    processes_raw_data = input_request_data['processes']
    
    try:
        time_quantum_value = int(input_request_data.get('quantum', 2))
    except ValueError:
        return jsonify(error="Invalid value for Time Quantum in comparison. Must be an integer."), 400
    
    comparison_results = []
    
    ALGORITHMS_TO_COMPARE = [
        ('FCFS', solve_fcfs, False),
        ('SJF', solve_sjf, False),
        ('Round Robin', solve_round_robin, True)
    ]
    
    for algorithm_name, solver_function, is_preemptive in ALGORITHMS_TO_COMPARE:
        
        process_objects_list = []
        for process_index, process_raw_data in enumerate(processes_raw_data):
            process_id = f"P{process_index+1}"
            try:
                arrival_time = int(process_raw_data[1])
                burst_time = int(process_raw_data[2])
                priority_level = int(process_raw_data[3]) if len(process_raw_data) > 3 and process_raw_data[3] else None
                process_objects_list.append(Process(process_id, arrival_time, burst_time, priority_level))
            except (ValueError, IndexError) as error_detail:
                return jsonify(error=f"Invalid process input for {algorithm_name} comparison: {error_detail}"), 400

        if is_preemptive:
            final_scheduled_jobs, gantt_chart_timeline = solver_function(process_objects_list, time_quantum_value)
        else:
            final_scheduled_jobs = solver_function(process_objects_list)
            gantt_chart_timeline = [{'pid': job.pid, 'start': job.ct - job.bt - job.wt, 'end': job.ct} for job in final_scheduled_jobs]

        performance_metrics = calculate_metrics(final_scheduled_jobs, gantt_chart_timeline)
        
        comparison_results.append({
            'algorithm': algorithm_name,
            'avg_wt': performance_metrics.get('avg_wt', 0.0), 
            'avg_tat': performance_metrics.get('avg_tat', 0.0),
            'tei': performance_metrics.get('tei', 0.0)
        })

    return jsonify(results=comparison_results)


if __name__ == '__main__':
    application_server.run(debug=True)