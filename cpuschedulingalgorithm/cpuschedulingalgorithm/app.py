from flask import Flask, render_template, request, jsonify
from scheduler import (
    Process, solve_fcfs, solve_round_robin, solve_sjf, solve_srtf,
    solve_priority, solve_priority_preemptive, calculate_metrics
)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    algorithm = data.get('algorithm', 'fcfs')

    try:
        quantum = int(data.get('quantum', 2))
    except ValueError:
        return jsonify(error="Invalid value for Time Quantum. Must be an integer."), 400

    processes = []
    for i, p_data in enumerate(data['processes']):
        pid = f"P{i+1}"
        try:
            at = int(p_data[1])
            bt = int(p_data[2])
            pr = int(p_data[3]) if len(p_data) > 3 and p_data[3] else None
            processes.append(Process(pid, at, bt, pr))
        except (ValueError, IndexError) as e:
            print(f"Error parsing process data: {e}")
            return jsonify(error="Invalid process input (AT, BT, or Priority). Check that all values are numbers."), 400

    scheduled_processes = []
    gantt_timeline = []

    try:
        if algorithm in ['fcfs', 'sjf', 'priority']:
            if algorithm == 'fcfs':
                scheduled_processes = solve_fcfs(processes)
            elif algorithm == 'sjf':
                scheduled_processes = solve_sjf(processes)
            elif algorithm == 'priority':
                scheduled_processes = solve_priority(processes)

            gantt_timeline = [
                {'pid': p.pid, 'start': p.ct - p.bt - p.wt, 'end': p.ct}
                for p in scheduled_processes
            ]

        elif algorithm == 'rr':
            scheduled_processes, gantt_timeline = solve_round_robin(processes, quantum)

        elif algorithm == 'srtf':
            scheduled_processes, gantt_timeline = solve_srtf(processes)

        elif algorithm == 'priority_preemptive':
            scheduled_processes, gantt_timeline = solve_priority_preemptive(processes)

        else:
            return jsonify(error=f"Algorithm '{algorithm}' not supported."), 400

    except Exception as e:
        print(f"Error during calculation for {algorithm}: {e}")
        return jsonify(error=f"Calculation Failed: {e}"), 500

    final_metrics = calculate_metrics(scheduled_processes, gantt_timeline)
    results = [p.to_dict() for p in scheduled_processes]

    return jsonify(
        results=results,
        gantt_timeline=gantt_timeline,
        metrics=final_metrics
    )


@app.route('/compare', methods=['POST'])
def compare():
    data = request.json
    processes_data = data['processes']

    try:
        quantum = int(data.get('quantum', 2))
    except ValueError:
        return jsonify(error="Invalid value for Time Quantum in comparison. Must be an integer."), 400

    comparison_results = []

    ALGORITHMS_TO_COMPARE = [
        ('FCFS', solve_fcfs, False),
        ('SJF', solve_sjf, False),
        ('Round Robin', solve_round_robin, True)
    ]

    for name, solver, is_preemptive in ALGORITHMS_TO_COMPARE:
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

        if is_preemptive:
            scheduled_processes, gantt_timeline = solver(processes, quantum)
        else:
            scheduled_processes = solver(processes)
            gantt_timeline = [
                {'pid': p.pid, 'start': p.ct - p.bt - p.wt, 'end': p.ct}
                for p in scheduled_processes
            ]

        metrics = calculate_metrics(scheduled_processes, gantt_timeline)

        comparison_results.append({
            'algorithm': name,
            'avg_wt': metrics.get('avg_wt', 0.0),
            'avg_tat': metrics.get('avg_tat', 0.0),
            'tei': metrics.get('tei', 0.0)
        })

    return jsonify(results=comparison_results)


if __name__ == '__main__':
    app.run(debug=True)
