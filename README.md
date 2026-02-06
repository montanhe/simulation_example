# simulation_example
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
