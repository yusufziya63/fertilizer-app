import streamlit as st
from pulp import LpProblem, LpMinimize, LpVariable, lpSum

def optimize_fertilizer(n, p, k, ca, mg, targets):
    # Define fertilizer prices
    prices = {'Fertilizer1': 20, 'Fertilizer2': 25, 'Fertilizer3': 30, 'Fertilizer4': 15, 'Fertilizer5': 22, 'Fertilizer6': 40, 'Fertilizer7': 35}

    # Create the optimization problem
    prob = LpProblem("Fertilizer Optimization", LpMinimize)
    amount_vars = {name: LpVariable(name, 0) for name in prices.keys()}

    # Objective function
    prob += lpSum([prices[name] * amount_vars[name] for name in prices])

    # Constraints
    prob += lpSum([amount_vars[name] for name in prices]) == targets
    prob += lpSum([amount_vars[name] * (n/100) for name in prices]) >= n
    prob += lpSum([amount_vars[name] * (p/100) for name in prices]) >= p
    prob += lpSum([amount_vars[name] * (k/100) for name in prices]) >= k
    prob += lpSum([amount_vars[name] * (ca/100) for name in prices]) >= ca
    prob += lpSum([amount_vars[name] * (mg/100) for name in prices]) >= mg

    prob.solve()

    # Results
    results = {name: amount_vars[name].varValue for name in prices}
    return results

st.title('Fertilizer Optimization App')
st.header('Optimize Your Fertilizer Usage')

# Period Selection
period = st.selectbox('Select Period:', ['14 days', '28 days', '56 days', '98 days'])

# Target Inputs
n = st.number_input('Enter N target:', min_value=0)
p = st.number_input('Enter P target:', min_value=0)
k = st.number_input('Enter K target:', min_value=0)
ca = st.number_input('Enter Ca target:', min_value=0)
mg = st.number_input('Enter Mg target:', min_value=0)
targets = st.number_input('Enter total amount of targets:', min_value=0)

# Price Inputs
st.subheader('Fertilizer Prices')
price_inputs = {f'Fertilizer {i+1}': st.number_input(f'Price of Fertilizer {i+1}:', min_value=0) for i in range(7)}

# Optimization Button
if st.button('Optimize!'):
    results = optimize_fertilizer(n, p, k, ca, mg, targets)
    st.write('### Results')
    for name, amount in results.items():
        st.write(f'{name}: {amount}')  
    # Display additional information (e.g., EC value and pH classification)
    st.write('### Additional Information')
    st.write('EC Value: ...')  
    st.write('pH Classification: ...') 

# Professional UI Enhancements
st.markdown("### 🎉 Welcome to the Fertilizer Optimization App! 🌱")
st.sidebar.markdown("### Use the options to the left to customize your inputs!")
