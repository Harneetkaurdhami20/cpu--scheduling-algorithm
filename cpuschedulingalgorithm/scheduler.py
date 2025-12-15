# scheduler.py

import math

class Process:
    """Represents a single process and its metrics."""
    def __init__(self, pid, arrival_time, burst_time, priority=None):
        self.pid = pid
        self.at = int(arrival_time)
        self.bt = int(burst_time)
        # Priority is an optional parameter (used for Priority algorithms)
        self.pr = int(priority) if priority is not None else None
        
        self.ct = 0  # Completion Time
        self.tat = 0 # Turnaround Time (TAT = CT - AT)
        self.wt = 0  # Waiting Time (WT = TAT - BT)

    def to_dict(self):
        """Converts object to dictionary for JSON transfer."""
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

# --- METRICS CALCULATIONS ---

def calculate_metrics(processes, gantt_timeline):
    """Calculates CPU Utilization, Throughput, and Energy Consumption."""
    if not processes:
        return {'utilization': 0.0, 'throughput': 0.0, 'energy': 0.0}

    # 1. Total Time and CPU Time
    last_event_time = 0
    if gantt_timeline:
        last_event_time = gantt_timeline[-1]['end']
    elif processes:
        # Fallback for non-timeline algorithms (last CT)
        last_event_time = max(p.ct for p in processes)

    total_cpu_time = sum(p.bt for p in processes)
    
    # 2. CPU Utilization
    if last_event_time > 0:
        utilization = (total_cpu_time / last_event_time) * 100
    else:
        utilization = 0.0
    
    # 3. Throughput
    # Throughput is processes completed per unit time
    if last_event_time > 0:
        throughput = len(processes) / last_event_time
    else:
        throughput = 0.0
    
    # 4. Energy Consumption (Simple model: Energy = Power * Time)
    # Assume: 
    # - Power for CPU use (Active): 5 Watts
    # - Power for Idle: 1 Watt
    
    cpu_active_time = total_cpu_time
    cpu_idle_time = last_event_time - cpu_active_time

    energy_consumed = (cpu_active_time * 5) + (cpu_idle_time * 1) # Energy in Watt-units (Joules)
    max_run_time = 0
    max_idle_time = 0
    current_run_time = 0
    current_idle_time = 0
    
    for block in gantt_timeline:
        duration = block['end'] - block['start']
        
        if block['pid'] == 'Idle':
            # Update Idle max
            current_idle_time += duration
            current_run_time = 0 
            if current_idle_time > max_idle_time:
                max_idle_time = current_idle_time
        else:
            # Update Run max
            current_run_time += duration
            current_idle_time = 0
            if current_run_time > max_run_time:
                max_run_time = current_run_time
    
    # b. Normalization
    # Assume a normalization constant (e.g., 10 units of time)
    MAX_TIME = 10 
    
    # Normalize C_F (penalty increases if max_run_time > MAX_TIME)
    normalized_cf = max_run_time / MAX_TIME
    
    # Normalize I_P (penalty increases if max_idle_time is large)
    normalized_ip = max_idle_time / MAX_TIME
    
    # c. Calculate Baseline Metrics
    total_tat = sum(p.tat for p in processes)
    avg_tat = total_tat / len(processes)
    total_wt = sum(p.wt for p in processes)
    avg_wt = total_wt / len(processes)

    # d. Calculate TEI
    if avg_tat > 0:
        tei = (avg_wt / avg_tat) + normalized_cf + normalized_ip
    else:
        tei = normalized_cf + normalized_ip # Avoid division by zero
    return {
        'utilization': round(utilization, 2),
        'throughput': round(throughput, 4),
        'energy': round(energy_consumed, 2),
        'tei': round(tei, 4)
    }

# --- ALGORITHMS (FCFS, RR, SJF, SRTF remain unchanged) ---

def solve_fcfs(processes):
    processes.sort(key=lambda x: x.at)
    current_time = 0
    for p in processes:
        if current_time < p.at: current_time = p.at
        p.ct = current_time + p.bt
        p.tat = p.ct - p.at
        p.wt = p.tat - p.bt
        current_time = p.ct
    return processes

# scheduler.py (The full, working Round Robin function)

def solve_round_robin(processes, quantum):
    """Implements Round Robin scheduling."""
    ready_queue = []
    finished_processes = []
    gantt_timeline = []
    
    # Structure to hold processes and their remaining time
    temp_processes = sorted(
        [{'p': p, 'rem_bt': p.bt} for p in processes], 
        key=lambda x: x['p'].at
    )
    
    time = 0
    process_index = 0
    
    while finished_processes.__len__() < processes.__len__() or ready_queue:
        
        # A. Check for new arrivals
        while process_index < len(temp_processes) and temp_processes[process_index]['p'].at <= time:
            ready_queue.append(temp_processes[process_index])
            process_index += 1
            
        # B. Handle Idle Time
        if not ready_queue:
            if process_index < len(temp_processes):
                next_arrival_time = temp_processes[process_index]['p'].at
                if time < next_arrival_time:
                    gantt_timeline.append({'pid': 'Idle', 'start': time, 'end': next_arrival_time})
                    time = next_arrival_time
                    continue
            else:
                break 

        # C. Execute the Process (FIFO order)
        current_job = ready_queue.pop(0)
        p_obj = current_job['p']
        
        execution_time = min(quantum, current_job['rem_bt'])
        start_time = time
        time += execution_time
        current_job['rem_bt'] -= execution_time
        
        # Merge if the last block was the same process
        if gantt_timeline and gantt_timeline[-1]['pid'] == p_obj.pid:
             gantt_timeline[-1]['end'] = time
        else:
             gantt_timeline.append({'pid': p_obj.pid, 'start': start_time, 'end': time})
        
        # D. Check for Completion or Preemption
        newly_arrived = []
        while process_index < len(temp_processes) and temp_processes[process_index]['p'].at <= time:
            newly_arrived.append(temp_processes[process_index])
            process_index += 1
            
        if current_job['rem_bt'] == 0:
            # Finished
            p_obj.ct = time
            p_obj.tat = p_obj.ct - p_obj.at
            p_obj.wt = p_obj.tat - p_obj.bt
            finished_processes.append(p_obj)
        else:
            # Preempted (must go to the end of the queue, after new arrivals)
            ready_queue.extend(newly_arrived)
            ready_queue.append(current_job)
            continue

        ready_queue.extend(newly_arrived)

    return finished_processes, gantt_timeline # <--- Crucial two-value return

# scheduler.py (Add these functions)

# --- 3. Non-Preemptive SJF ---

def solve_sjf(processes):
    """Implements Non-Preemptive Shortest Job First. 
    Returns the final list of scheduled processes."""
    
    # 1. Setup
    # Sort initially by arrival time
    temp_processes = sorted(processes, key=lambda x: x.at)
    ready_queue = []
    scheduled_processes = []
    current_time = 0
    process_index = 0

    while len(scheduled_processes) < len(processes):
        
        # A. Move newly arrived processes to the Ready Queue
        while process_index < len(temp_processes) and temp_processes[process_index].at <= current_time:
            ready_queue.append(temp_processes[process_index])
            process_index += 1

        # B. Handle Idle Time
        if not ready_queue:
            if process_index < len(temp_processes):
                # Idle: Advance time to the next arrival
                current_time = temp_processes[process_index].at
                continue
            else:
                # All jobs finished/accounted for
                break 

        # C. Select the Shortest Job (The core of SJF!)
        # Sort by burst time (bt). Tie-breaker: Arrival Time (at).
        ready_queue.sort(key=lambda x: (x.bt, x.at))
        
        current_job = ready_queue.pop(0)

        # D. Execute (Non-Preemptive)
        current_job.ct = current_time + current_job.bt
        current_job.tat = current_job.ct - current_job.at
        current_job.wt = current_job.tat - current_job.bt
        
        current_time = current_job.ct
        scheduled_processes.append(current_job)
        
    return scheduled_processes

# --- 4. SRTF (Preemptive SJF) ---

def solve_srtf(processes):
    """Implements Shortest Remaining Time First (SRTF - Preemptive SJF).
    Returns: Final processes list and the Gantt timeline."""
    
    # 1. Setup
    finished_processes = []
    gantt_timeline = []
    
    # Use a dictionary structure to track remaining burst time
    temp_processes = sorted(
        [{'p': p, 'rem_bt': p.bt} for p in processes], 
        key=lambda x: x['p'].at
    )
    
    ready_queue = []
    current_time = 0
    process_index = 0
    last_pid = None # Used for merging Gantt blocks

    while len(finished_processes) < len(processes):
        
        # A. Move new arrivals to the Ready Queue
        while process_index < len(temp_processes) and temp_processes[process_index]['p'].at <= current_time:
            ready_queue.append(temp_processes[process_index])
            process_index += 1
            
        # B. Selection: Always choose process with minimum rem_bt
        if ready_queue:
            # Sort by remaining burst time (rem_bt). Tie-breaker: Arrival Time (at).
            ready_queue.sort(key=lambda x: (x['rem_bt'], x['p'].at))
            current_job = ready_queue.pop(0)
        else:
            current_job = None

        # C. Handle Idle Time
        if not current_job:
            if process_index < len(temp_processes):
                next_arrival_time = temp_processes[process_index]['p'].at
                if current_time < next_arrival_time:
                    # Record idle block and jump time
                    gantt_timeline.append({'pid': 'Idle', 'start': current_time, 'end': next_arrival_time})
                    current_time = next_arrival_time
                    last_pid = 'Idle'
                    continue
            else:
                break
        
        # D. Determine Execution Duration
        execution_duration = current_job['rem_bt']
        
        # Check for preemption due to the next arrival
        if process_index < len(temp_processes):
            next_arrival_time = temp_processes[process_index]['p'].at
            time_until_arrival = next_arrival_time - current_time 
            
            # Preempt if a new process arrives before the current job finishes
            if time_until_arrival > 0 and time_until_arrival < current_job['rem_bt']:
                execution_duration = time_until_arrival
        
        # E. Execute and Record
        start_time = current_time
        current_time += execution_duration
        current_job['rem_bt'] -= execution_duration
        
        current_pid = current_job['p'].pid
        if gantt_timeline and last_pid == current_pid:
             # Merge with the last block if the process is the same
             gantt_timeline[-1]['end'] = current_time
        else:
             gantt_timeline.append({'pid': current_pid, 'start': start_time, 'end': current_time})
             last_pid = current_pid

        # F. Handle Completion
        if current_job['rem_bt'] == 0:
            p_obj = current_job['p']
            p_obj.ct = current_time
            p_obj.tat = p_obj.ct - p_obj.at
            p_obj.wt = p_obj.tat - p_obj.bt
            finished_processes.append(p_obj)
        else:
            # Job was preempted; put it back in the ready queue
            ready_queue.append(current_job)
            
    return finished_processes, gantt_timeline


# --- 5. NON-PREEMPTIVE PRIORITY ---

def solve_priority(processes):
    """Implements Non-Preemptive Priority Scheduling (Lower number = Higher Priority)."""
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
                current_time = temp_processes[process_index].at
                continue
            else:
                break 

        # C. Select the Highest Priority Job
        # Sort by priority (pr), then by arrival time (at) for ties (FCFS)
        ready_queue.sort(key=lambda x: (x.pr, x.at))
        
        current_job = ready_queue.pop(0)

        # D. Execute (Non-Preemptive)
        current_job.ct = current_time + current_job.bt
        current_job.tat = current_job.ct - current_job.at
        current_job.wt = current_job.tat - current_job.bt
        
        current_time = current_job.ct
        scheduled_processes.append(current_job)
        
    return scheduled_processes

# --- 6. PREEMPTIVE PRIORITY ---

def solve_priority_preemptive(processes):
    """Implements Preemptive Priority Scheduling (Lower number = Higher Priority)."""
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
        
        # A. Move new arrivals to the Ready Queue
        new_arrivals_occurred = False
        while process_index < len(temp_processes) and temp_processes[process_index]['p'].at <= current_time:
            ready_queue.append(temp_processes[process_index])
            process_index += 1
            new_arrivals_occurred = True
            
        # B. Selection: Always choose process with minimum priority (pr)
        if ready_queue:
            # Sort by priority (pr), then by arrival time (at) for ties (FCFS)
            ready_queue.sort(key=lambda x: (x['p'].pr, x['p'].at))
            current_job = ready_queue.pop(0)
        else:
            current_job = None

        # C. Handle Idle Time
        if not current_job:
            if process_index < len(temp_processes):
                next_arrival_time = temp_processes[process_index]['p'].at
                if current_time < next_arrival_time:
                    gantt_timeline.append({'pid': 'Idle', 'start': current_time, 'end': next_arrival_time})
                    current_time = next_arrival_time
                    last_pid = 'Idle'
                    continue
            else:
                break
        
        # D. Determine Execution Duration
        execution_duration = current_job['rem_bt']
        
        # Check for preemption due to the next arrival (which may have a higher priority)
        if process_index < len(temp_processes):
            next_arrival_time = temp_processes[process_index]['p'].at
            time_until_arrival = next_arrival_time - current_time 
            
            # Check if the next arriving job has higher priority (lower pr number)
            next_pr = temp_processes[process_index]['p'].pr
            current_pr = current_job['p'].pr
            
            if time_until_arrival > 0 and next_pr < current_pr:
                # Preempt now, run only until the next arrival
                execution_duration = time_until_arrival
            
            elif time_until_arrival > 0 and time_until_arrival < current_job['rem_bt'] and next_pr >= current_pr:
                 # Standard preemption check for SRTF/RR-style timeline (only run until completion/quantum/next event)
                 # Since this is priority, if the next arrival has lower or equal priority, we only preempt if the job finishes.
                 pass # We run until completion by default here, as the priority won't change.


        # E. Execute and Record
        start_time = current_time
        current_time += execution_duration
        current_job['rem_bt'] -= execution_duration
        
        current_pid = current_job['p'].pid
        if gantt_timeline and last_pid == current_pid:
             gantt_timeline[-1]['end'] = current_time
        else:
             gantt_timeline.append({'pid': current_pid, 'start': start_time, 'end': current_time})
             last_pid = current_pid

        # F. Handle Completion
        if current_job['rem_bt'] == 0:
            p_obj = current_job['p']
            p_obj.ct = current_time
            p_obj.tat = p_obj.ct - p_obj.at
            p_obj.wt = p_obj.tat - p_obj.bt
            finished_processes.append(p_obj)
        else:
            # Put preempted job back in the queue
            ready_queue.append(current_job)
            
    return finished_processes, gantt_timeline