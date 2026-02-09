import math
import simpy
import random
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from scipy.optimize import minimize


###############################################################################
# Setup streamlit
###############################################################################
st.set_page_config(page_title='Simulation & Optimization', layout='wide')
st.title('Production Line Simulation & Optimization')

###############################################################################
# Fixed Parameters
###############################################################################
st.sidebar.header('Fixed Parameters')
l1 = 30
C1 = 500
C2 = 500
n_machines = 3
setup_time_machine1 = 10
setup_time_machine2 = 5

st.sidebar.metric('Arrival Rate', l1)
st.sidebar.metric('Max Capacity at WIP1', C1)
st.sidebar.metric('Max Capacity at WIP2', C2)
st.sidebar.metric('Number of Machines', n_machines)
st.sidebar.metric('Setup Time Machine 1', setup_time_machine1)
st.sidebar.metric('Setup Time Machine 2', setup_time_machine2)

###############################################################################
# User Input Parameters
###############################################################################
st.sidebar.header('Adjustable Parameters')
SIM_TIME = st.sidebar.slider('Simulation Time (minutes)', 
                               min_value=60, max_value=300, value=120, step=10)
k1 = st.sidebar.slider('Processing Rate k1 (units/min)', 
                          min_value=30.0, max_value=50.0, value=30.0, step=1.0)
k2 = st.sidebar.slider('Processing Rate k2 (units/min)', 
                          min_value=15.0, max_value=40.0, value=20.0, step=1.0)
k3 = st.sidebar.slider('Processing Rate k3 (units/min)',
                             min_value=1.0, max_value=7.0, value=5.0, step=1.0)

###############################################################################
# Define Simulation Functions
###############################################################################
def order_arrivals(env, machine):
    '''
       Orders arrive at machine1 following a Poisson process with ratio l1
    '''
    while True:
        inter = random.expovariate(l1)
        yield env.timeout(inter)

def machine1(env, machine, wip1, k, restart_time):
    '''
       Machine1 takes units from its input queue, processes them at rate k.
       Pushes them into WIP1 as long as WIP1 is not full
    '''
    proc_time = 1.0 / k

    while True:
        req = machine.request()
        yield req

        if len(wip1.items) >= C1:
            machine.release(req)
            yield env.timeout(restart_time)
            continue

        yield env.timeout(proc_time)
        yield wip1.put(1)
        machine.release(req)

def machine2(env, wip1, machine, wip2, k, restart_time):
    '''
       Machine2 process units from WIP1 at rate k. Switches OFF when WIP2 is
       full. Restarts after restart_time when space available
    '''
    proc_time = 1.0 / k

    while True:
        yield wip1.get()
        req = machine.request()
        yield req

        if len(wip2.items) >= C2:
            machine.release(req)
            yield env.timeout(restart_time)
            continue

        yield env.timeout(proc_time)
        yield wip2.put(1)
        machine.release(req)

def machine3_unit(env, wip2, k, counter):
    '''
       Single cutting machine - takes units from WIP2 and process at rate k.
       Sends the processed item out
    '''
    proc_time = 1.0 / k
    while True:
        yield wip2.get()
        yield env.timeout(proc_time)
        counter[0] += 1

def machine3_fleet(env, wip2, k, n_machines, counter):
    '''
       Launch parallel machines multiple cutter machines in parallel
    '''
    for i in range(n_machines):
        env.process(machine3_unit(env, wip2, k, counter))
    while True:
        yield env.timeout(1)

def monitor(env, wip1, wip2, completed_units, records):
    '''
       Record total occupation of both WIP areas and completed units every full minute.
    '''
    while True:
        t = math.floor(env.now)
        records.append((t, len(wip1.items), len(wip2.items), completed_units[0]))
        yield env.timeout(1.0)
    
def run_simulation_monitor(k1, k2, k3, sim_time):
    '''
       Run the simulation with rates k1, k2 and k3 and setup a monitor to 
       retrieve statistics.
    ''' 
    completed_units = [0] 
    random.seed(42)

    env = simpy.Environment()
    mach1 = simpy.Resource(env, capacity=1)
    mach2 = simpy.Resource(env, capacity=1)
    wip1 = simpy.Store(env, capacity=C1)
    wip2 = simpy.Store(env, capacity=C2)

    env.process(order_arrivals(env, mach1))
    env.process(machine1(env, mach1, wip1, k1, setup_time_machine1))
    env.process(machine2(env, wip1, mach2, wip2, k2, setup_time_machine2))
    env.process(machine3_fleet(env, wip2, k3, n_machines, completed_units))

    records = []
    env.process(monitor(env, wip1, wip2, completed_units, records))

    env.run(until=sim_time)
    return records

def plot_results(results, title_suffix=''):
    '''
       Plot WIP levels and production over time
    '''
    minutes = [r[0] for r in results]
    wip1_occ = [r[1] for r in results]
    wip2_occ = [r[2] for r in results]
    cum_completed = [r[3] for r in results]

    fig = make_subplots(rows=3, cols=1,
                        subplot_titles=('WIP before Machine2',
                                      'WIP before Machine3',
                                      'Total units fully produced'),
                        vertical_spacing=0.08,
                        shared_xaxes=True)

    fig.add_trace(go.Scatter(x=minutes, y=wip1_occ, mode='lines+markers', 
                            name='WIP1', line=dict(color='blue')), row=1, col=1)

    fig.add_trace(go.Scatter(x=minutes, y=wip2_occ, mode='lines+markers',
                            name='WIP2', line=dict(color='orange')), row=2, col=1)

    fig.add_trace(go.Scatter(x=minutes, y=cum_completed, mode='lines+markers',
                            name='Total Produced', line=dict(color='green')), row=3, col=1)

    fig.update_layout(height=900,
                     title_text=f'WIP Levels and Production Over Time {title_suffix}',
                     showlegend=True,
                     xaxis3=dict(title='Time (minutes)', range=[0, max(minutes)]))
    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(showgrid=True)

    return fig

###############################################################################
# Action Buttons
###############################################################################
if st.button("Run Simulation", type="primary"):
    with st.spinner("Running simulation..."):
        results = run_simulation_monitor(k1, k2, k3, SIM_TIME)

        st.success("Simulation completed!")

        # Display metrics
        final_wip1 = results[-1][1]
        final_wip2 = results[-1][2]
        total_produced = results[-1][3]

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Total Units Produced", total_produced)
        metric_col2.metric("Final WIP1", final_wip1)
        metric_col3.metric("Final WIP2", final_wip2)

        # Plot results
        fig = plot_results(results)
        st.plotly_chart(fig, use_container_width=True)

###############################################################################
# Information Section
###############################################################################
with st.expander('About this Application'):
    st.markdown('''
    This application simulates a production line with three machines and two
    work-in-progress (WIP) areas.

    **Production Flow:**
    1. Orders arrive at Machine 1 following a Poisson process
    2. Machine 1 processes units and stores them in WIP1 (before Machine 2)
    3. Machine 2 processes units from WIP1 and stores them in WIP2 (before 
       Machine 3)
    4. Machine 3 (fleet of parallel machines) processes units from WIP2 and 
       completes them

    **Parameters:**
    - **k1, k2, k3**: Processing rates (units/minute) for each machine
    - **SIM_TIME**: Total simulation time in minutes
    - **Fixed parameters**: Arrival rate, capacity limits, setup times

    **Actions:**
    - **Run Simulation**: Runs the simulation with your selected parameters
    ''')
