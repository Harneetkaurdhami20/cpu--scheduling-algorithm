import math

class Process:
    def __init__(self, pid, arrival_time, burst_time, priority=None):
        self.pid = pid
        # Ensure conversion to int happens correctly
        self.at = int(arrival_time)
        self.bt = int(burst_time)
        self.pr = int(priority) if priority is not None and str(priority).isdigit() else None
        self.ct = 0
        self.tat = 0
        self.wt = 0

    def to_dict(self):
        data = {
            'pid': self.pid,
            'at': self.at,
            'bt': self.bt,
            'ct': self.ct,
            'tat': self.tat,
            'wt': self.wt
        }
        if self.pr is not None:
            data['pr'] = self.pr
        return data


def calculate_metrics(processes, gantt_timeline):
    if not processes:
        return {
            'avg_tat': 0.0,
            'avg_wt': 0.0,
            'utilization': 0.0,
            'throughput': 0.0,
            'energy': 0.0,
            'tei': 0.0
        }

    # --- 1. Average Metrics Calculation ---
    total_tat = sum(p.tat for p in processes)
    total_wt = sum(p.wt for p in processes)
    num_processes = len(processes)
    
    avg_tat = total_tat / num_processes
    avg_wt = total_wt / num_processes

    # --- 2. Utilization & Throughput Calculation ---
    last_event_time = 0
    if gantt_timeline:
        last_event_time = gantt_timeline[-1]['end']
    elif processes:
        # In case non-preemptive algorithms don't produce a full gantt timeline
        last_event_time = max(p.ct for p in processes) if processes else 0

    total_cpu_time = sum(p.bt for p in processes)

    if last_event_time > 0:
        utilization = (total_cpu_time / last_event_time) * 100
        throughput = len(processes) / last_event_time
    else:
        utilization = 0.0
        throughput = 0.0

    # --- 3. Energy and TEI Calculation ---
    cpu_active_time = total_cpu_time
    cpu_idle_time = last_event_time - cpu_active_time
    # Increased power factor for active vs idle time
    energy_consumed = (cpu_active_time * 5) + (cpu_idle_time * 1) 

    max_run_time = 0
    max_idle_time = 0
    current_run_time = 0
    current_idle_time = 0

    for block in gantt_timeline:
        duration = block['end'] - block['start']
        if block['pid'] == 'Idle':
            current_idle_time += duration
            current_run_time = 0
            max_idle_time = max(max_idle_time, current_idle_time)
        else:
            current_run_time += duration
            current_idle_time = 0
            max_run_time = max(max_run_time, current_run_time)

    MAX_TIME = 10 # Normalization factor
    normalized_cf = max_run_time / MAX_TIME
    normalized_ip = max_idle_time / MAX_TIME

    # TEI formula: (Avg_WT / Avg_TAT) + Normalized_Continuous_Run_Time + Normalized_Idle_Time
    if avg_tat > 0:
        tei = (avg_wt / avg_tat) + normalized_cf + normalized_ip
    else:
        tei = normalized_cf + normalized_ip

    # --- 4. Final Return Dictionary (with all required keys) ---
    return {
        # 📢 FIX: Added avg_tat and avg_wt to the return dictionary
        'avg_tat': avg_tat,
        'avg_wt': avg_wt, 
        'utilization': utilization,
        'throughput': throughput,
        'energy': energy_consumed,
        'tei': tei
    }


def solve_fcfs(processes):
    processes.sort(key=lambda x: x.at)
    current_time = 0
    for p in processes:
        if current_time < p.at:
            current_time = p.at
        p.ct = current_time + p.bt
        p.tat = p.ct - p.at
        p.wt = p.tat - p.bt
        current_time = p.ct
    return processes


def solve_round_robin(processes, quantum):
    ready_queue = []
    finished_processes = []
    gantt_timeline = []

    temp_processes = sorted(
        [{'p': p, 'rem_bt': p.bt} for p in processes],
        key=lambda x: x['p'].at
    )

    time = 0
    process_index = 0

    while len(finished_processes) < len(processes) or ready_queue:

        while process_index < len(temp_processes) and temp_processes[process_index]['p'].at <= time:
            ready_queue.append(temp_processes[process_index])
            process_index += 1

        if not ready_queue:
            if process_index < len(temp_processes):
                next_arrival_time = temp_processes[process_index]['p'].at
                if time < next_arrival_time:
                    gantt_timeline.append({'pid': 'Idle', 'start': time, 'end': next_arrival_time})
                    time = next_arrival_time
                    continue
            else:
                break

        current_job = ready_queue.pop(0)
        p_obj = current_job['p']

        execution_time = min(quantum, current_job['rem_bt'])
        start_time = time
        time += execution_time
        current_job['rem_bt'] -= execution_time

        if gantt_timeline and gantt_timeline[-1]['pid'] == p_obj.pid:
            gantt_timeline[-1]['end'] = time
        else:
            gantt_timeline.append({'pid': p_obj.pid, 'start': start_time, 'end': time})

        newly_arrived = []
        while process_index < len(temp_processes) and temp_processes[process_index]['p'].at <= time:
            newly_arrived.append(temp_processes[process_index])
            process_index += 1

        if current_job['rem_bt'] == 0:
            p_obj.ct = time
            p_obj.tat = p_obj.ct - p_obj.at
            p_obj.wt = p_obj.tat - p_obj.bt
            finished_processes.append(p_obj)
        else:
            ready_queue.extend(newly_arrived)
            ready_queue.append(current_job)
            continue

        ready_queue.extend(newly_arrived)

    return finished_processes, gantt_timeline


def solve_sjf(processes):
    temp_processes = sorted(processes, key=lambda x: x.at)
    ready_queue = []
    scheduled_processes = []
    current_time = 0
    process_index = 0

    while len(scheduled_processes) < len(processes):

        while process_index < len(temp_processes) and temp_processes[process_index].at <= current_time:
            ready_queue.append(temp_processes[process_index])
            process_index += 1

        if not ready_queue:
            if process_index < len(temp_processes):
                # Idle time until next arrival
                current_time = temp_processes[process_index].at
                continue
            else:
                break

        # Sort by Burst Time, then by Arrival Time (SJF)
        ready_queue.sort(key=lambda x: (x.bt, x.at))
        current_job = ready_queue.pop(0)

        current_job.ct = current_time + current_job.bt
        current_job.tat = current_job.ct - current_job.at
        current_job.wt = current_job.tat - current_job.bt

        current_time = current_job.ct
        scheduled_processes.append(current_job)

    return scheduled_processes


def solve_srtf(processes):
    finished_processes = []
    gantt_timeline = []

    temp_processes = sorted(
        [{'p': p, 'rem_bt': p.bt} for p in processes],
        key=lambda x: x['p'].at
    )

    ready_queue = []
    current_time = 0
    process_index = 0
    last_pid = None

    while len(finished_processes) < len(processes):

        while process_index < len(temp_processes) and temp_processes[process_index]['p'].at <= current_time:
            ready_queue.append(temp_processes[process_index])
            process_index += 1

        if ready_queue:
            # Sort by remaining burst time (SRTF), then by arrival time
            ready_queue.sort(key=lambda x: (x['rem_bt'], x['p'].at))
            current_job = ready_queue.pop(0)
        else:
            current_job = None

        if not current_job:
            if process_index < len(temp_processes):
                next_arrival_time = temp_processes[process_index]['p'].at
                if current_time < next_arrival_time:
                    if gantt_timeline and gantt_timeline[-1]['pid'] == 'Idle':
                        gantt_timeline[-1]['end'] = next_arrival_time
                    else:
                        gantt_timeline.append({'pid': 'Idle', 'start': current_time, 'end': next_arrival_time})
                    current_time = next_arrival_time
                    last_pid = 'Idle'
                    continue
            else:
                break

        execution_duration = current_job['rem_bt']

        if process_index < len(temp_processes):
            next_arrival_time = temp_processes[process_index]['p'].at
            time_until_arrival = next_arrival_time - current_time
            # Check for preemption possibility
            if 0 < time_until_arrival and temp_processes[process_index]['rem_bt'] < current_job['rem_bt']:
                 execution_duration = time_until_arrival
            elif 0 < time_until_arrival < current_job['rem_bt']:
                 # Run until next arrival if it's shorter than remaining burst
                 execution_duration = time_until_arrival


        start_time = current_time
        current_time += execution_duration
        current_job['rem_bt'] -= execution_duration

        current_pid = current_job['p'].pid
        if gantt_timeline and last_pid == current_pid:
            gantt_timeline[-1]['end'] = current_time
        else:
            gantt_timeline.append({'pid': current_pid, 'start': start_time, 'end': current_time})
            last_pid = current_pid

        if current_job['rem_bt'] == 0:
            p_obj = current_job['p']
            p_obj.ct = current_time
            p_obj.tat = p_obj.ct - p_obj.at
            p_obj.wt = p_obj.tat - p_obj.bt
            finished_processes.append(p_obj)
        else:
            ready_queue.append(current_job)

    return finished_processes, gantt_timeline


def solve_priority(processes):
    temp_processes = sorted(processes, key=lambda x: x.at)
    ready_queue = []
    scheduled_processes = []
    current_time = 0
    process_index = 0

    while len(scheduled_processes) < len(processes):

        while process_index < len(temp_processes) and temp_processes[process_index].at <= current_time:
            ready_queue.append(temp_processes[process_index])
            process_index += 1

        if not ready_queue:
            if process_index < len(temp_processes):
                # Idle time until next arrival
                current_time = temp_processes[process_index].at
                continue
            else:
                break

        # Sort by Priority (lowest number is highest priority), then by Arrival Time
        ready_queue.sort(key=lambda x: (x.pr, x.at))
        current_job = ready_queue.pop(0)

        current_job.ct = current_time + current_job.bt
        current_job.tat = current_job.ct - current_job.at
        current_job.wt = current_job.tat - current_job.bt

        current_time = current_job.ct
        scheduled_processes.append(current_job)

    return scheduled_processes


def solve_priority_preemptive(processes):
    finished_processes = []
    gantt_timeline = []

    temp_processes = sorted(
        [{'p': p, 'rem_bt': p.bt} for p in processes],
        key=lambda x: x['p'].at
    )

    ready_queue = []
    current_time = 0
    process_index = 0
    last_pid = None

    while len(finished_processes) < len(processes):

        while process_index < len(temp_processes) and temp_processes[process_index]['p'].at <= current_time:
            ready_queue.append(temp_processes[process_index])
            process_index += 1

        if ready_queue:
            # Sort by Priority (lowest number is highest), then by arrival time
            ready_queue.sort(key=lambda x: (x['p'].pr, x['p'].at))
            current_job = ready_queue.pop(0)
        else:
            current_job = None

        if not current_job:
            if process_index < len(temp_processes):
                next_arrival_time = temp_processes[process_index]['p'].at
                if current_time < next_arrival_time:
                    if gantt_timeline and gantt_timeline[-1]['pid'] == 'Idle':
                        gantt_timeline[-1]['end'] = next_arrival_time
                    else:
                        gantt_timeline.append({'pid': 'Idle', 'start': current_time, 'end': next_arrival_time})
                    current_time = next_arrival_time
                    last_pid = 'Idle'
                    continue
            else:
                break

        execution_duration = current_job['rem_bt']

        if process_index < len(temp_processes):
            next_arrival_time = temp_processes[process_index]['p'].at
            time_until_arrival = next_arrival_time - current_time
            next_pr = temp_processes[process_index]['p'].pr
            current_pr = current_job['p'].pr

            # Check for preemption possibility (Lower PR value means higher priority)
            if 0 < time_until_arrival and next_pr < current_pr:
                execution_duration = time_until_arrival
            elif 0 < time_until_arrival < current_job['rem_bt']:
                 # Run until next arrival if it's shorter than remaining burst (general efficiency check)
                 execution_duration = time_until_arrival

        start_time = current_time
        current_time += execution_duration
        current_job['rem_bt'] -= execution_duration

        current_pid = current_job['p'].pid
        if gantt_timeline and last_pid == current_pid:
            gantt_timeline[-1]['end'] = current_time
        else:
            gantt_timeline.append({'pid': current_pid, 'start': start_time, 'end': current_time})
            last_pid = current_pid

        if current_job['rem_bt'] == 0:
            p_obj = current_job['p']
            p_obj.ct = current_time
            p_obj.tat = p_obj.ct - p_obj.at
            p_obj.wt = p_obj.tat - p_obj.bt
            finished_processes.append(p_obj)
        else:
            ready_queue.append(current_job)

    return finished_processes, gantt_timeline