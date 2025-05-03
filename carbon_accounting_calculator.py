import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import base64

# Set page configuration
st.set_page_config(
    page_title="Carbon Footprint Calculator for Indian Companies",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2e7d32;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2e7d32;
        margin-bottom: 0.5rem;
    }
    .description {
        font-size: 1rem;
        margin-bottom: 1rem;
    }
    .highlight {
        background-color: #f1f8e9;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .footer {
        text-align: center;
        margin-top: 2rem;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
if 'data' not in st.session_state:
    st.session_state.data = {
        'company_info': {},
        'scope1': {},
        'scope2': {},
        'scope3': {},
        'results': {},
        'history': []
    }

if 'page' not in st.session_state:
    st.session_state.page = 'home'

if 'industry' not in st.session_state:
    st.session_state.industry = None

# -------------------------- EMISSION FACTORS DATABASE --------------------------

# These emission factors are based on India-specific data where available
# Sources include: Bureau of Energy Efficiency (BEE), Central Electricity Authority (CEA),
# IPCC Guidelines, and industry reports specific to the Indian context

# Electricity emission factors (kg CO2e per kWh) - India grid average (Source: CEA)
ELECTRICITY_EF = 0.82  # kg CO2e/kWh for Indian grid average

# Fuel emission factors (kg CO2e per unit)
FUEL_EF = {
    'Natural Gas': 2.07,  # kg CO2e/m3
    'Diesel': 2.68,  # kg CO2e/liter
    'Petrol': 2.31,  # kg CO2e/liter
    'LPG': 2.99,  # kg CO2e/kg
    'Coal': 2.42,  # kg CO2e/kg
    'Furnace Oil': 3.15,  # kg CO2e/liter
    'Kerosene': 2.52,  # kg CO2e/liter
    'Biomass': 0.05,  # kg CO2e/kg (significantly lower due to biogenic carbon)
}

# Transportation emission factors (kg CO2e per km)
TRANSPORT_EF = {
    'Car (Petrol)': 0.19,  # kg CO2e/km
    'Car (Diesel)': 0.17,  # kg CO2e/km
    'Car (CNG)': 0.14,  # kg CO2e/km
    'Car (Electric)': 0.05,  # kg CO2e/km (depends on electricity source)
    'Two Wheeler': 0.07,  # kg CO2e/km
    'Bus': 0.03,  # kg CO2e/passenger-km
    'Train': 0.01,  # kg CO2e/passenger-km
    'Domestic Flight': 0.14,  # kg CO2e/passenger-km
    'International Flight': 0.18,  # kg CO2e/passenger-km
    'Light Commercial Vehicle': 0.25,  # kg CO2e/km
    'Heavy Commercial Vehicle': 0.85,  # kg CO2e/km
}

# Material emission factors (kg CO2e per kg of material)
MATERIAL_EF = {
    'Steel': 2.6,  # kg CO2e/kg (India-specific data)
    'Aluminum': 16.5,  # kg CO2e/kg
    'Cement': 0.83,  # kg CO2e/kg
    'Plastic (General)': 3.4,  # kg CO2e/kg
    'Glass': 0.91,  # kg CO2e/kg
    'Paper': 1.5,  # kg CO2e/kg
    'Textiles': 15.0,  # kg CO2e/kg
    'Electronics': 25.0,  # kg CO2e/kg (varies widely by specific item)
    'Food (General)': 3.0,  # kg CO2e/kg (varies by food type)
    'Wood': 0.45,  # kg CO2e/kg
}

# Water treatment and waste disposal (kg CO2e per cubic meter or ton)
WASTE_WATER_EF = {
    'Water Supply': 0.34,  # kg CO2e/m3
    'Wastewater Treatment': 0.71,  # kg CO2e/m3
    'Landfill Waste': 458.0,  # kg CO2e/ton
    'Recycled Waste': 21.0,  # kg CO2e/ton
    'Composted Waste': 10.0,  # kg CO2e/ton
    'Incinerated Waste': 580.0,  # kg CO2e/ton
}

# Industry-specific process emission factors
INDUSTRY_PROCESS_EF = {
    'Manufacturing': {
        'Cement Production': 520.0,  # kg CO2e/ton of cement
        'Steel Production': 1800.0,  # kg CO2e/ton of steel
        'Chemical Processing': 1200.0,  # kg CO2e/ton of products
        'Textile Processing': 15.0,  # kg CO2e/kg of textiles
        'Food Processing': 2.5,  # kg CO2e/kg of processed food
        'Electronics Manufacturing': 30.0,  # kg CO2e/unit (varies by product)
    },
    'Hospitality': {
        'Laundry Operations': 0.6,  # kg CO2e/kg of laundry
        'Food Service': 8.0,  # kg CO2e/meal
        'Refrigerant Leakage': 1800.0,  # kg CO2e/kg of refrigerant (average GWP)
        'Pool Heating': 0.24,  # kg CO2e/m3 of water heated
    },
    'Energy': {
        'Coal Power Generation': 1.05,  # kg CO2e/kWh
        'Natural Gas Power Generation': 0.54,  # kg CO2e/kWh
        'Oil Power Generation': 0.75,  # kg CO2e/kWh
        'Solar Power Generation': 0.05,  # kg CO2e/kWh (lifecycle)
        'Wind Power Generation': 0.01,  # kg CO2e/kWh (lifecycle)
        'Hydro Power Generation': 0.02,  # kg CO2e/kWh (lifecycle)
        'Nuclear Power Generation': 0.04,  # kg CO2e/kWh (lifecycle)
        'Biomass Power Generation': 0.23,  # kg CO2e/kWh
        'Transmission Losses': 0.04,  # kg CO2e/kWh transmitted
    },
    'Automobile': {
        'Painting Process': 18.0,  # kg CO2e/vehicle
        'Welding Process': 12.0,  # kg CO2e/vehicle
        'Assembly Line': 60.0,  # kg CO2e/vehicle
        'Testing Operations': 15.0,  # kg CO2e/vehicle
        'Refrigerant Charging': 25.0,  # kg CO2e/vehicle
    }
}

# Industry benchmarks (kg CO2e per unit)
# These are representative averages for the Indian market
INDUSTRY_BENCHMARKS = {
    'Manufacturing': {
        'per_product': 250.0,  # kg CO2e per unit product (varies by product type)
        'per_revenue': 0.15,  # kg CO2e per INR of revenue
        'per_employee': 4500.0,  # kg CO2e per employee per year
        'intensity_target': 0.12,  # target kg CO2e per INR of revenue
    },
    'Hospitality': {
        'per_guest_night': 25.0,  # kg CO2e per guest night
        'per_revenue': 0.08,  # kg CO2e per INR of revenue
        'per_employee': 3200.0,  # kg CO2e per employee per year
        'per_room': 8500.0,  # kg CO2e per room per year
        'intensity_target': 0.06,  # target kg CO2e per INR of revenue
    },
    'Energy': {
        'per_kWh_generated': 0.70,  # kg CO2e per kWh generated
        'per_revenue': 0.40,  # kg CO2e per INR of revenue
        'per_employee': 12000.0,  # kg CO2e per employee per year
        'intensity_target': 0.32,  # target kg CO2e per INR of revenue
    },
    'Automobile': {
        'per_vehicle': 5500.0,  # kg CO2e per vehicle manufactured
        'per_revenue': 0.12,  # kg CO2e per INR of revenue
        'per_employee': 6000.0,  # kg CO2e per employee per year
        'intensity_target': 0.09,  # target kg CO2e per INR of revenue
    }
}

# -------------------------- UTILITY FUNCTIONS --------------------------

def calculate_scope1_emissions(fuel_data, industry_process_data, refrigerant_data, company_vehicles_data):
    """Calculate Scope 1 emissions from direct sources"""
    emissions = 0
    
    # Stationary combustion (fuels)
    for fuel, amount in fuel_data.items():
        if fuel in FUEL_EF and amount > 0:
            fuel_emissions = amount * FUEL_EF[fuel]
            emissions += fuel_emissions
    
    # Industry-specific process emissions
    industry = st.session_state.industry
    if industry:
        for process, amount in industry_process_data.items():
            if process in INDUSTRY_PROCESS_EF.get(industry, {}) and amount > 0:
                process_emissions = amount * INDUSTRY_PROCESS_EF[industry][process]
                emissions += process_emissions
    
    # Refrigerant leakage
    for refrigerant, amount in refrigerant_data.items():
        # Using a standard GWP for refrigerants if specific ones aren't listed
        refrigerant_emissions = amount * 1800.0  # Average GWP for common refrigerants
        emissions += refrigerant_emissions
    
    # Company-owned vehicles
    for vehicle_type, distance in company_vehicles_data.items():
        if vehicle_type in TRANSPORT_EF and distance > 0:
            transport_emissions = distance * TRANSPORT_EF[vehicle_type]
            emissions += transport_emissions
    
    return emissions

def calculate_scope2_emissions(electricity_data):
    """Calculate Scope 2 emissions from purchased electricity"""
    emissions = 0
    
    # Purchased electricity
    grid_electricity = electricity_data.get('Grid Electricity', 0)
    emissions += grid_electricity * ELECTRICITY_EF
    
    # Green electricity (with lower emission factor)
    green_electricity = electricity_data.get('Green Electricity', 0)
    emissions += green_electricity * 0.05  # Assuming much lower EF for green electricity
    
    return emissions

def calculate_scope3_emissions(business_travel_data, employee_commute_data, waste_data, 
                               purchased_goods_data, transportation_data, water_data):
    """Calculate Scope 3 emissions from indirect sources"""
    emissions = 0
    
    # Business travel
    for transport_type, distance in business_travel_data.items():
        if transport_type in TRANSPORT_EF and distance > 0:
            travel_emissions = distance * TRANSPORT_EF[transport_type]
            emissions += travel_emissions
    
    # Employee commuting
    for transport_type, distance in employee_commute_data.items():
        if transport_type in TRANSPORT_EF and distance > 0:
            commute_emissions = distance * TRANSPORT_EF[transport_type]
            emissions += commute_emissions
    
    # Waste disposal
    for waste_type, amount in waste_data.items():
        if waste_type in WASTE_WATER_EF and amount > 0:
            waste_emissions = amount * WASTE_WATER_EF[waste_type]
            emissions += waste_emissions
    
    # Purchased goods and services
    for material, amount in purchased_goods_data.items():
        if material in MATERIAL_EF and amount > 0:
            material_emissions = amount * MATERIAL_EF[material]
            emissions += material_emissions
    
    # Upstream and downstream transportation
    for transport_type, distance in transportation_data.items():
        if transport_type in TRANSPORT_EF and distance > 0:
            transport_emissions = distance * TRANSPORT_EF[transport_type]
            emissions += transport_emissions
    
    # Water usage
    for water_type, amount in water_data.items():
        if water_type in WASTE_WATER_EF and amount > 0:
            water_emissions = amount * WASTE_WATER_EF[water_type]
            emissions += water_emissions
    
    return emissions

def generate_recommendations(emissions_data, industry):
    """Generate industry-specific recommendations based on emissions profile"""
    recommendations = []
    
    # General recommendations for all industries
    recommendations.append("1. Set science-based targets for emissions reduction aligned with Paris Agreement goals")
    recommendations.append("2. Implement an energy management system (like ISO 50001) to monitor and optimize energy use")
    recommendations.append("3. Consider renewable energy options such as solar panel installation or renewable energy certificates")
    
    # Check which scope has the highest emissions and focus recommendations there
    scope1 = emissions_data.get('Scope 1', 0)
    scope2 = emissions_data.get('Scope 2', 0)
    scope3 = emissions_data.get('Scope 3', 0)
    
    highest_scope = max(scope1, scope2, scope3)
    
    if scope1 == highest_scope:
        if industry == 'Manufacturing':
            recommendations.append("4. Upgrade to high-efficiency furnaces and boilers with heat recovery systems")
            recommendations.append("5. Implement process optimization to reduce material and energy inputs")
            recommendations.append("6. Consider fuel switching from coal or oil to natural gas or biomass")
        elif industry == 'Hospitality':
            recommendations.append("4. Implement a comprehensive kitchen energy efficiency program")
            recommendations.append("5. Upgrade to high-efficiency HVAC systems and improve building insulation")
            recommendations.append("6. Install smart room controls to reduce energy use in unoccupied spaces")
        elif industry == 'Energy':
            recommendations.append("4. Implement carbon capture technologies for fossil fuel power plants")
            recommendations.append("5. Reduce methane leakage in natural gas infrastructure")
            recommendations.append("6. Increase the efficiency of power generation units through upgrades")
        elif industry == 'Automobile':
            recommendations.append("4. Optimize paint booth operations to reduce VOC emissions and energy use")
            recommendations.append("5. Improve process efficiency in welding and assembly operations")
            recommendations.append("6. Implement heat recovery systems throughout manufacturing processes")
    
    elif scope2 == highest_scope:
        recommendations.append("4. Purchase renewable energy directly through power purchase agreements")
        recommendations.append("5. Implement an LED lighting retrofit program across all facilities")
        recommendations.append("6. Install smart meters and energy management systems to identify reduction opportunities")
        
    elif scope3 == highest_scope:
        if industry == 'Manufacturing':
            recommendations.append("4. Engage with suppliers to reduce embodied carbon in raw materials")
            recommendations.append("5. Optimize logistics to reduce transportation emissions")
            recommendations.append("6. Redesign products for lower lifecycle carbon footprint")
        elif industry == 'Hospitality':
            recommendations.append("4. Implement a sustainable procurement policy for food and consumables")
            recommendations.append("5. Encourage sustainable transportation options for guests")
            recommendations.append("6. Reduce food waste through better inventory management and composting")
        elif industry == 'Energy':
            recommendations.append("4. Reduce transmission and distribution losses through grid upgrades")
            recommendations.append("5. Implement lifecycle assessment for infrastructure projects")
            recommendations.append("6. Partner with end-users on energy efficiency programs")
        elif industry == 'Automobile':
            recommendations.append("4. Work with suppliers to reduce emissions in component manufacturing")
            recommendations.append("5. Optimize logistics and supply chain operations")
            recommendations.append("6. Design vehicles for improved fuel efficiency and lower lifecycle emissions")
    
    return recommendations

def calculate_benchmark_comparison(total_emissions, company_info, industry):
    """Compare emissions with industry benchmarks"""
    benchmark_data = {}
    
    if industry in INDUSTRY_BENCHMARKS:
        # Get relevant company metrics for comparison
        revenue = company_info.get('revenue', 0)
        employees = company_info.get('employees', 0)
        
        if industry == 'Manufacturing':
            production_volume = company_info.get('production_volume', 0)
            if production_volume > 0:
                per_product_actual = total_emissions / production_volume
                per_product_benchmark = INDUSTRY_BENCHMARKS[industry]['per_product']
                benchmark_data['per_product'] = {
                    'actual': per_product_actual,
                    'benchmark': per_product_benchmark,
                    'percent_diff': ((per_product_actual - per_product_benchmark) / per_product_benchmark) * 100
                }
                
        elif industry == 'Hospitality':
            guest_nights = company_info.get('guest_nights', 0)
            rooms = company_info.get('rooms', 0)
            
            if guest_nights > 0:
                per_guest_night_actual = total_emissions / guest_nights
                per_guest_night_benchmark = INDUSTRY_BENCHMARKS[industry]['per_guest_night']
                benchmark_data['per_guest_night'] = {
                    'actual': per_guest_night_actual,
                    'benchmark': per_guest_night_benchmark,
                    'percent_diff': ((per_guest_night_actual - per_guest_night_benchmark) / per_guest_night_benchmark) * 100
                }
                
            if rooms > 0:
                per_room_actual = total_emissions / rooms
                per_room_benchmark = INDUSTRY_BENCHMARKS[industry]['per_room']
                benchmark_data['per_room'] = {
                    'actual': per_room_actual,
                    'benchmark': per_room_benchmark,
                    'percent_diff': ((per_room_actual - per_room_benchmark) / per_room_benchmark) * 100
                }
                
        elif industry == 'Energy':
            energy_generated = company_info.get('energy_generated', 0)
            
            if energy_generated > 0:
                per_kwh_actual = total_emissions / energy_generated
                per_kwh_benchmark = INDUSTRY_BENCHMARKS[industry]['per_kWh_generated']
                benchmark_data['per_kWh_generated'] = {
                    'actual': per_kwh_actual,
                    'benchmark': per_kwh_benchmark,
                    'percent_diff': ((per_kwh_actual - per_kwh_benchmark) / per_kwh_benchmark) * 100
                }
                
        elif industry == 'Automobile':
            vehicles_produced = company_info.get('vehicles_produced', 0)
            
            if vehicles_produced > 0:
                per_vehicle_actual = total_emissions / vehicles_produced
                per_vehicle_benchmark = INDUSTRY_BENCHMARKS[industry]['per_vehicle']
                benchmark_data['per_vehicle'] = {
                    'actual': per_vehicle_actual,
                    'benchmark': per_vehicle_benchmark,
                    'percent_diff': ((per_vehicle_actual - per_vehicle_benchmark) / per_vehicle_benchmark) * 100
                }
        
        # Common metrics for all industries
        if revenue > 0:
            per_revenue_actual = total_emissions / revenue
            per_revenue_benchmark = INDUSTRY_BENCHMARKS[industry]['per_revenue']
            intensity_target = INDUSTRY_BENCHMARKS[industry]['intensity_target']
            benchmark_data['per_revenue'] = {
                'actual': per_revenue_actual,
                'benchmark': per_revenue_benchmark,
                'target': intensity_target,
                'percent_diff': ((per_revenue_actual - per_revenue_benchmark) / per_revenue_benchmark) * 100
            }
            
        if employees > 0:
            per_employee_actual = total_emissions / employees
            per_employee_benchmark = INDUSTRY_BENCHMARKS[industry]['per_employee']
            benchmark_data['per_employee'] = {
                'actual': per_employee_actual,
                'benchmark': per_employee_benchmark,
                'percent_diff': ((per_employee_actual - per_employee_benchmark) / per_employee_benchmark) * 100
            }
    
    return benchmark_data

def create_downloadable_excel(data):
    """Create a downloadable Excel report with all emissions data"""
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Company Information Sheet
    company_df = pd.DataFrame([data['company_info']])
    company_df.to_excel(writer, sheet_name='Company Information', index=False)
    
    # Emissions Summary Sheet
    summary_data = {
        'Scope': ['Scope 1', 'Scope 2', 'Scope 3', 'Total'],
        'Emissions (kg CO2e)': [
            data['results']['scope1_emissions'],
            data['results']['scope2_emissions'],
            data['results']['scope3_emissions'],
            data['results']['total_emissions']
        ],
        'Percentage': [
            data['results']['scope1_percentage'],
            data['results']['scope2_percentage'],
            data['results']['scope3_percentage'],
            100.0
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_excel(writer, sheet_name='Emissions Summary', index=False)
    
    # Detailed Emissions Sheets
    # Scope 1
    scope1_df = pd.DataFrame({
        'Category': list(data['scope1'].keys()),
        'Value': list(data['scope1'].values())
    })
    scope1_df.to_excel(writer, sheet_name='Scope 1 Detailed', index=False)
    
    # Scope 2
    scope2_df = pd.DataFrame({
        'Category': list(data['scope2'].keys()),
        'Value': list(data['scope2'].values())
    })
    scope2_df.to_excel(writer, sheet_name='Scope 2 Detailed', index=False)
    
    # Scope 3
    scope3_data = {}
    for key, value_dict in data['scope3'].items():
        for subkey, value in value_dict.items():
            scope3_data[f"{key} - {subkey}"] = value
    
    scope3_df = pd.DataFrame({
        'Category': list(scope3_data.keys()),
        'Value': list(scope3_data.values())
    })
    scope3_df.to_excel(writer, sheet_name='Scope 3 Detailed', index=False)
    
    # Benchmark Comparison
    if 'benchmark_data' in data['results']:
        benchmark_rows = []
        for metric, values in data['results']['benchmark_data'].items():
            benchmark_rows.append({
                'Metric': metric,
                'Actual': values.get('actual', 0),
                'Benchmark': values.get('benchmark', 0),
                'Percent Difference': values.get('percent_diff', 0)
            })
        benchmark_df = pd.DataFrame(benchmark_rows)
        benchmark_df.to_excel(writer, sheet_name='Benchmark Comparison', index=False)
    
    # Recommendations
    if 'recommendations' in data['results']:
        recommendations_df = pd.DataFrame({
            'Recommendations': data['results']['recommendations']
        })
        recommendations_df.to_excel(writer, sheet_name='Recommendations', index=False)
    
    # Save and close
    writer.close()
    
    # Convert to base64 for download
    b64 = base64.b64encode(output.getvalue()).decode()
    return b64

# -------------------------- PAGE COMPONENTS --------------------------

def render_home_page():
    """Render the home page with app introduction"""
    st.markdown("<h1 class='main-header'>Carbon Footprint Calculator</h1>", unsafe_allow_html=True)
    st.markdown("<h2 class='sub-header'>For Indian Companies</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class='description'>
        Welcome to the comprehensive carbon footprint calculator designed specifically for Indian companies.
        This tool helps you measure, track, and reduce your greenhouse gas emissions across all three scopes
        as defined by the GHG Protocol.
        </div>
        
        <div class='highlight'>
        <strong>Features:</strong>
        <ul>
            <li>Industry-specific calculations for Manufacturing, Hospitality, Energy, and Automobile sectors</li>
            <li>GHG Protocol compliant methodology covering Scope 1, 2, and 3 emissions</li>
            <li>India-specific emission factors for accurate calculations</li>
            <li>Interactive visualizations and benchmarking capabilities</li>
            <li>Tailored recommendations for emission reduction</li>
            <li>Historical tracking and downloadable reports</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<h3 class='sub-header'>Getting Started</h3>", unsafe_allow_html=True)
        st.markdown("""
        <ol>
            <li>Select your industry sector</li>
            <li>Enter your company information</li>
            <li>Provide data for all three emission scopes</li>
            <li>Review your carbon footprint results and recommendations</li>
            <li>Download your detailed report</li>
        </ol>
        """, unsafe_allow_html=True)
    
    with col2:
        st.image("https://via.placeholder.com/300x400.png?text=Carbon+Footprint", width=300)
    
    st.markdown("<h3 class='sub-header'>Select Your Industry</h3>", unsafe_allow_html=True)
    industry = st.selectbox(
        "Choose your industry sector:",
        ["Manufacturing", "Hospitality", "Energy", "Automobile"]
    )
    
    if st.button("Continue", key="home_continue"):
        st.session_state.industry = industry
        st.session_state.page = 'company_info'
        st.experimental_rerun()

def render_company_info_page():
    """Render the company information input page"""
    st.markdown("<h1 class='main-header'>Company Information</h1>", unsafe_allow_html=True)
    
    with st.form("company_info_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            company_name = st.text_input("Company Name", value=st.session_state.data['company_info'].get('company_name', ''))
            industry = st.selectbox(
                "Industry",
                ["Manufacturing", "Hospitality", "Energy", "Automobile"],
                index=["Manufacturing", "Hospitality", "Energy", "Automobile"].index(st.session_state.industry)
            )
            reporting_year = st.selectbox(
                "Reporting Year",
                list(range(datetime.now().year, datetime.now().year - 10, -1)),
                index=0
            )
            employees = st.number_input(
                "Number of Employees",
                min_value=1,
                value=st.session_state.data['company_info'].get('employees', 100)
            )
            
        with col2:
            revenue = st.number_input(
                "Annual Revenue (in Lakhs INR)",
                min_value=0.0,
                value=st.session_state.data['company_info'].get('revenue', 1000.0)
            )
            
            # Industry-specific inputs
            if industry == "Manufacturing":
                production_volume = st.number_input(
                    "Annual Production Volume (units)",
                    min_value=0,
                    value=st.session_state.data['company_info'].get('production_volume', 10000)
                )
                facility_area = st.number_input(
                    "Facility Area (sq. meters)",
                    min_value=0,
                    value=st.session_state.data['company_info'].get('facility_area', 5000)
                )
                
            elif industry == "Hospitality":
                rooms = st.number_input(
                    "Number of Rooms",
                    min_value=0,
                    value=st.session_state.data['company_info'].get('rooms', 100)
                )
                guest_nights = st.number_input(
                    "Annual Guest Nights",
                    min_value=0,
                    value=st.session_state.data['company_info'].get('guest_nights', 25000)
                )
                
            elif industry == "Energy":
                energy_generated = st.number_input(
                    "Annual Energy Generated (MWh)",
                    min_value=0,
                    value=st.session_state.data['company_info'].get('energy_generated', 500000)
                )
                generation_type = st.selectbox(
                    "Primary Generation Type",
                    ["Coal", "Natural Gas", "Solar", "Wind", "Hydro", "Nuclear", "Biomass", "Mixed"],
                    index=0
                )
                
            elif industry == "Automobile":
                vehicles_produced = st.number_input(
                    "Annual Vehicles Produced",
                    min_value=0,
                    value=st.session_state.data['company_info'].get('vehicles_produced', 50000)
                )
                vehicle_type = st.selectbox(
                    "Primary Vehicle Type",
                    ["Passenger Cars", "Commercial Vehicles", "Two-Wheelers", "Three-Wheelers", "Mixed"],
                    index=0
                )
                
        submitted = st.form_submit_button("Save and Continue")
        
        if submitted:
            # Save company info to session state
            company_info = {
                'company_name': company_name,
                'industry': industry,
                'reporting_year': reporting_year,
                'employees': employees,
                'revenue': revenue
            }
            
            # Add industry-specific fields
            if industry == "Manufacturing":
                company_info['production_volume'] = production_volume
                company_info['facility_area'] = facility_area
            elif industry == "Hospitality":
                company_info['rooms'] = rooms
                company_info['guest_nights'] = guest_nights
            elif industry == "Energy":
                company_info['energy_generated'] = energy_generated
                company_info['generation_type'] = generation_type
            elif industry == "Automobile":
                company_info['vehicles_produced'] = vehicles_produced
                company_info['vehicle_type'] = vehicle_type
            
            st.session_state.data['company_info'] = company_info
            st.session_state.industry = industry
            st.session_state.page = 'scope1'
            st.experimental_rerun()
    
    # Navigation buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Back to Home", key="company_back"):
            st.session_state.page = 'home'
            st.experimental_rerun()

def render_scope1_page():
    """Render the Scope 1 emissions input page"""
    st.markdown("<h1 class='main-header'>Scope 1 Emissions</h1>", unsafe_allow_html=True)
    st.markdown("""
    <div class='description'>
    Scope 1 emissions are direct emissions from owned or controlled sources. This includes:
    <ul>
        <li>Fuel consumption in company facilities</li>
        <li>Company-owned vehicles</li>
        <li>Process emissions specific to your industry</li>
        <li>Fugitive emissions (e.g., refrigerant leakage)</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("scope1_form"):
        st.subheader("Stationary Combustion")
        st.markdown("Enter the annual consumption of fuels used in your facilities:")
        
        col1, col2 = st.columns(2)
        
        fuel_data = {}
        with col1:
            fuel_data['Natural Gas'] = st.number_input(
                "Natural Gas (cubic meters)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Natural Gas', 0.0)
            )
            fuel_data['Diesel'] = st.number_input(
                "Diesel (liters)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Diesel', 0.0)
            )
            fuel_data['LPG'] = st.number_input(
                "LPG (kg)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('LPG', 0.0)
            )
            fuel_data['Coal'] = st.number_input(
                "Coal (kg)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Coal', 0.0)
            )
        
        with col2:
            fuel_data['Petrol'] = st.number_input(
                "Petrol (liters)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Petrol', 0.0)
            )
            fuel_data['Furnace Oil'] = st.number_input(
                "Furnace Oil (liters)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Furnace Oil', 0.0)
            )
            fuel_data['Kerosene'] = st.number_input(
                "Kerosene (liters)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Kerosene', 0.0)
            )
            fuel_data['Biomass'] = st.number_input(
                "Biomass (kg)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Biomass', 0.0)
            )
        
        # Industry-specific process emissions
        st.subheader("Process Emissions")
        st.markdown("Enter data for industry-specific processes:")
        
        industry = st.session_state.industry
        industry_process_data = {}
        
        col1, col2 = st.columns(2)
        with col1:
            if industry == "Manufacturing":
                industry_process_data['Cement Production'] = st.number_input(
                    "Cement Production (tons)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Cement Production', 0.0)
                )
                industry_process_data['Steel Production'] = st.number_input(
                    "Steel Production (tons)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Steel Production', 0.0)
                )
                industry_process_data['Chemical Processing'] = st.number_input(
                    "Chemical Processing (tons)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Chemical Processing', 0.0)
                )
                
            elif industry == "Hospitality":
                industry_process_data['Laundry Operations'] = st.number_input(
                    "Laundry Operations (kg)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Laundry Operations', 0.0)
                )
                industry_process_data['Food Service'] = st.number_input(
                    "Food Service (meals served)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Food Service', 0.0)
                )
                industry_process_data['Pool Heating'] = st.number_input(
                    "Pool Heating (cubic meters of water)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Pool Heating', 0.0)
                )
                
            elif industry == "Energy":
                industry_process_data['Coal Power Generation'] = st.number_input(
                    "Coal Power Generation (MWh)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Coal Power Generation', 0.0)
                )
                industry_process_data['Natural Gas Power Generation'] = st.number_input(
                    "Natural Gas Power Generation (MWh)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Natural Gas Power Generation', 0.0)
                )
                industry_process_data['Oil Power Generation'] = st.number_input(
                    "Oil Power Generation (MWh)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Oil Power Generation', 0.0)
                )
                
            elif industry == "Automobile":
                industry_process_data['Painting Process'] = st.number_input(
                    "Painting Process (vehicles)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Painting Process', 0.0)
                )
                industry_process_data['Welding Process'] = st.number_input(
                    "Welding Process (vehicles)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Welding Process', 0.0)
                )
                industry_process_data['Assembly Line'] = st.number_input(
                    "Assembly Line (vehicles)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Assembly Line', 0.0)
                )
        
        with col2:
            if industry == "Manufacturing":
                industry_process_data['Textile Processing'] = st.number_input(
                    "Textile Processing (kg)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Textile Processing', 0.0)
                )
                industry_process_data['Food Processing'] = st.number_input(
                    "Food Processing (kg)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Food Processing', 0.0)
                )
                industry_process_data['Electronics Manufacturing'] = st.number_input(
                    "Electronics Manufacturing (units)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Electronics Manufacturing', 0.0)
                )
                
            elif industry == "Hospitality":
                industry_process_data['Refrigerant Leakage'] = st.number_input(
                    "Refrigerant Leakage (kg)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Refrigerant Leakage', 0.0)
                )
                
            elif industry == "Energy":
                industry_process_data['Biomass Power Generation'] = st.number_input(
                    "Biomass Power Generation (MWh)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Biomass Power Generation', 0.0)
                )
                industry_process_data['Transmission Losses'] = st.number_input(
                    "Transmission Losses (MWh)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Transmission Losses', 0.0)
                )
                
            elif industry == "Automobile":
                industry_process_data['Testing Operations'] = st.number_input(
                    "Testing Operations (vehicles)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Testing Operations', 0.0)
                )
                industry_process_data['Refrigerant Charging'] = st.number_input(
                    "Refrigerant Charging (vehicles)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('Refrigerant Charging', 0.0)
                )
        
        # Refrigerant leakage (common across industries, except for specific industry processes above)
        if industry != "Hospitality":  # Already included in industry-specific for Hospitality
            st.subheader("Fugitive Emissions")
            st.markdown("Enter data for refrigerant leakage from air conditioning and refrigeration systems:")
            
            refrigerant_data = {}
            col1, col2 = st.columns(2)
            
            with col1:
                refrigerant_data['R-410A'] = st.number_input(
                    "R-410A (kg)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('R-410A', 0.0)
                )
            
            with col2:
                refrigerant_data['R-22'] = st.number_input(
                    "R-22 (kg)",
                    min_value=0.0,
                    value=st.session_state.data.get('scope1', {}).get('R-22', 0.0)
                )
        else:
            refrigerant_data = {}
        
        # Company-owned vehicles
        st.subheader("Mobile Combustion")
        st.markdown("Enter the annual distance traveled by company-owned vehicles:")
        
        company_vehicles_data = {}
        col1, col2 = st.columns(2)
        
        with col1:
            company_vehicles_data['Car (Petrol)'] = st.number_input(
                "Cars - Petrol (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Car (Petrol)', 0.0)
            )
            company_vehicles_data['Car (Diesel)'] = st.number_input(
                "Cars - Diesel (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Car (Diesel)', 0.0)
            )
            
        with col2:
            company_vehicles_data['Car (CNG)'] = st.number_input(
                "Cars - CNG (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Car (CNG)', 0.0)
            )
            company_vehicles_data['Two Wheeler'] = st.number_input(
                "Two Wheelers (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Two Wheeler', 0.0)
            )
            
        col1, col2 = st.columns(2)
        with col1:
            company_vehicles_data['Light Commercial Vehicle'] = st.number_input(
                "Light Commercial Vehicles (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Light Commercial Vehicle', 0.0)
            )
            
        with col2:
            company_vehicles_data['Heavy Commercial Vehicle'] = st.number_input(
                "Heavy Commercial Vehicles (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope1', {}).get('Heavy Commercial Vehicle', 0.0)
            )
        
        submitted = st.form_submit_button("Save and Continue")
        
        if submitted:
            # Combine all scope 1 data
            scope1_data = {**fuel_data, **industry_process_data, **refrigerant_data, **company_vehicles_data}
            st.session_state.data['scope1'] = scope1_data
            st.session_state.page = 'scope2'
            st.experimental_rerun()
    
    # Navigation buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Back to Company Info", key="scope1_back"):
            st.session_state.page = 'company_info'
            st.experimental_rerun()

def render_scope2_page():
    """Render the Scope 2 emissions input page"""
    st.markdown("<h1 class='main-header'>Scope 2 Emissions</h1>", unsafe_allow_html=True)
    st.markdown("""
    <div class='description'>
    Scope 2 emissions are indirect emissions from purchased electricity, steam, heating, and cooling. For most companies in India, this is primarily from grid electricity consumption.
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("scope2_form"):
        st.subheader("Purchased Electricity")
        
        electricity_data = {}
        col1, col2 = st.columns(2)
        
        with col1:
            electricity_data['Grid Electricity'] = st.number_input(
                "Grid Electricity (kWh)",
                min_value=0.0,
                value=st.session_state.data.get('scope2', {}).get('Grid Electricity', 0.0)
            )
            
        with col2:
            electricity_data['Green Electricity'] = st.number_input(
                "Green Electricity - Solar, Wind, etc. (kWh)",
                min_value=0.0,
                value=st.session_state.data.get('scope2', {}).get('Green Electricity', 0.0)
            )
        
        submitted = st.form_submit_button("Save and Continue")
        
        if submitted:
            st.session_state.data['scope2'] = electricity_data
            st.session_state.page = 'scope3'
            st.experimental_rerun()
    
    # Navigation buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Back to Scope 1", key="scope2_back"):
            st.session_state.page = 'scope1'
            st.experimental_rerun()

def render_scope3_page():
    """Render the Scope 3 emissions input page"""
    st.markdown("<h1 class='main-header'>Scope 3 Emissions</h1>", unsafe_allow_html=True)
    st.markdown("""
    <div class='description'>
    Scope 3 emissions are all indirect emissions not included in scope 2 that occur in the value chain of the company, including both upstream and downstream emissions.
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("scope3_form"):
        # Business Travel
        st.subheader("Business Travel")
        st.markdown("Enter the annual distance traveled for business purposes:")
        
        business_travel_data = {}
        col1, col2 = st.columns(2)
        
        with col1:
            business_travel_data['Domestic Flight'] = st.number_input(
                "Domestic Flights (passenger-km)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('business_travel', {}).get('Domestic Flight', 0.0)
            )
            business_travel_data['International Flight'] = st.number_input(
                "International Flights (passenger-km)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('business_travel', {}).get('International Flight', 0.0)
            )
            
        with col2:
            business_travel_data['Car (Petrol)'] = st.number_input(
                "Rental/Taxi - Petrol (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('business_travel', {}).get('Car (Petrol)', 0.0)
            )
            business_travel_data['Train'] = st.number_input(
                "Train (passenger-km)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('business_travel', {}).get('Train', 0.0)
            )
        
        # Employee Commuting
        st.subheader("Employee Commuting")
        st.markdown("Enter the annual distance traveled by all employees for commuting:")
        
        employee_commute_data = {}
        col1, col2 = st.columns(2)
        
        with col1:
            employee_commute_data['Car (Petrol)'] = st.number_input(
                "Cars - Petrol (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('employee_commute', {}).get('Car (Petrol)', 0.0),
                key="ec_car_petrol"
            )
            employee_commute_data['Car (Diesel)'] = st.number_input(
                "Cars - Diesel (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('employee_commute', {}).get('Car (Diesel)', 0.0),
                key="ec_car_diesel"
            )
            employee_commute_data['Two Wheeler'] = st.number_input(
                "Two Wheelers (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('employee_commute', {}).get('Two Wheeler', 0.0),
                key="ec_two_wheeler"
            )
            
        with col2:
            employee_commute_data['Bus'] = st.number_input(
                "Bus (passenger-km)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('employee_commute', {}).get('Bus', 0.0)
            )
            employee_commute_data['Train'] = st.number_input(
                "Train (passenger-km)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('employee_commute', {}).get('Train', 0.0),
                key="ec_train"
            )
            employee_commute_data['Car (Electric)'] = st.number_input(
                "Cars - Electric (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('employee_commute', {}).get('Car (Electric)', 0.0)
            )
        
        # Waste Generated
        st.subheader("Waste Generated in Operations")
        st.markdown("Enter the annual amount of waste generated:")
        
        waste_data = {}
        col1, col2 = st.columns(2)
        
        with col1:
            waste_data['Landfill Waste'] = st.number_input(
                "Landfill Waste (tons)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('waste', {}).get('Landfill Waste', 0.0)
            )
            waste_data['Recycled Waste'] = st.number_input(
                "Recycled Waste (tons)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('waste', {}).get('Recycled Waste', 0.0)
            )
            
        with col2:
            waste_data['Composted Waste'] = st.number_input(
                "Composted Waste (tons)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('waste', {}).get('Composted Waste', 0.0)
            )
            waste_data['Incinerated Waste'] = st.number_input(
                "Incinerated Waste (tons)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('waste', {}).get('Incinerated Waste', 0.0)
            )
        
        # Purchased Goods & Services
        st.subheader("Purchased Goods & Services")
        st.markdown("Enter the annual amounts of key purchased materials:")
        
        purchased_goods_data = {}
        col1, col2 = st.columns(2)
        
        with col1:
            purchased_goods_data['Steel'] = st.number_input(
                "Steel (kg)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('purchased_goods', {}).get('Steel', 0.0)
            )
            purchased_goods_data['Aluminum'] = st.number_input(
                "Aluminum (kg)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('purchased_goods', {}).get('Aluminum', 0.0)
            )
            purchased_goods_data['Plastic (General)'] = st.number_input(
                "Plastic (kg)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('purchased_goods', {}).get('Plastic (General)', 0.0)
            )
            
        with col2:
            purchased_goods_data['Paper'] = st.number_input(
                "Paper (kg)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('purchased_goods', {}).get('Paper', 0.0)
            )
            purchased_goods_data['Glass'] = st.number_input(
                "Glass (kg)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('purchased_goods', {}).get('Glass', 0.0)
            )
            purchased_goods_data['Electronics'] = st.number_input(
                "Electronics (kg)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('purchased_goods', {}).get('Electronics', 0.0)
            )
        
        # Transportation & Distribution
        st.subheader("Upstream & Downstream Transportation")
        st.markdown("Enter the annual distances for transportation of goods:")
        
        transportation_data = {}
        col1, col2 = st.columns(2)
        
        with col1:
            transportation_data['Light Commercial Vehicle'] = st.number_input(
                "Light Commercial Vehicles (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('transportation', {}).get('Light Commercial Vehicle', 0.0),
                key="trans_lcv"
            )
            
        with col2:
            transportation_data['Heavy Commercial Vehicle'] = st.number_input(
                "Heavy Commercial Vehicles (km)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('transportation', {}).get('Heavy Commercial Vehicle', 0.0),
                key="trans_hcv"
            )
        
        # Water Usage
        st.subheader("Water Usage")
        st.markdown("Enter the annual water consumption and wastewater generated:")
        
        water_data = {}
        col1, col2 = st.columns(2)
        
        with col1:
            water_data['Water Supply'] = st.number_input(
                "Water Consumption (cubic meters)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('water', {}).get('Water Supply', 0.0)
            )
            
        with col2:
            water_data['Wastewater Treatment'] = st.number_input(
                "Wastewater Treatment (cubic meters)",
                min_value=0.0,
                value=st.session_state.data.get('scope3', {}).get('water', {}).get('Wastewater Treatment', 0.0)
            )
        
        submitted = st.form_submit_button("Save and Continue")
        
        if submitted:
            # Save all scope 3 data
            scope3_data = {
                'business_travel': business_travel_data,
                'employee_commute': employee_commute_data,
                'waste': waste_data,
                'purchased_goods': purchased_goods_data,
                'transportation': transportation_data,
                'water': water_data
            }
            
            st.session_state.data['scope3'] = scope3_data
            st.session_state.page = 'results'
            st.experimental_rerun()
    
    # Navigation buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Back to Scope 2", key="scope3_back"):
            st.session_state.page = 'scope2'
            st.experimental_rerun()

def render_results_page():
    """Render the results page with emissions calculations and visualizations"""
    st.markdown("<h1 class='main-header'>Carbon Footprint Results</h1>", unsafe_allow_html=True)
    
    # Calculate emissions if not already done
    if 'results' not in st.session_state.data or not st.session_state.data['results']:
        with st.spinner("Calculating your carbon footprint..."):
            # Calculate Scope 1 emissions
            scope1_emissions = calculate_scope1_emissions(
                st.session_state.data.get('scope1', {}),
                {k: v for k, v in st.session_state.data.get('scope1', {}).items() 
                 if k in INDUSTRY_PROCESS_EF.get(st.session_state.industry, {})},
                {k: v for k, v in st.session_state.data.get('scope1', {}).items() 
                 if k in ['R-410A', 'R-22']},
                {k: v for k, v in st.session_state.data.get('scope1', {}).items() 
                 if k in TRANSPORT_EF}
            )
            
            # Calculate Scope 2 emissions
            scope2_emissions = calculate_scope2_emissions(
                st.session_state.data.get('scope2', {})
            )
            
            # Calculate Scope 3 emissions
            scope3_emissions = calculate_scope3_emissions(
                st.session_state.data.get('scope3', {}).get('business_travel', {}),
                st.session_state.data.get('scope3', {}).get('employee_commute', {}),
                st.session_state.data.get('scope3', {}).get('waste', {}),
                st.session_state.data.get('scope3', {}).get('purchased_goods', {}),
                st.session_state.data.get('scope3', {}).get('transportation', {}),
                st.session_state.data.get('scope3', {}).get('water', {})
            )
            
            # Calculate total emissions and percentages
            total_emissions = scope1_emissions + scope2_emissions + scope3_emissions
            
            if total_emissions > 0:
                scope1_percentage = (scope1_emissions / total_emissions) * 100
                scope2_percentage = (scope2_emissions / total_emissions) * 100
                scope3_percentage = (scope3_emissions / total_emissions) * 100
            else:
                scope1_percentage = scope2_percentage = scope3_percentage = 0
            
            # Generate benchmark comparison
            benchmark_data = calculate_benchmark_comparison(
                total_emissions,
                st.session_state.data.get('company_info', {}),
                st.session_state.industry
            )
            
            # Generate recommendations
            recommendations = generate_recommendations(
                {
                    'Scope 1': scope1_emissions,
                    'Scope 2': scope2_emissions,
                    'Scope 3': scope3_emissions
                },
                st.session_state.industry
            )
            
            # Store results
            results = {
                'scope1_emissions': scope1_emissions,
                'scope2_emissions': scope2_emissions,
                'scope3_emissions': scope3_emissions,
                'total_emissions': total_emissions,
                'scope1_percentage': scope1_percentage,
                'scope2_percentage': scope2_percentage,
                'scope3_percentage': scope3_percentage,
                'benchmark_data': benchmark_data,
                'recommendations': recommendations
            }
            
            # Save results to session state
            st.session_state.data['results'] = results
            
            # Add to history if not already there
            current_data = {
                'date': datetime.now().strftime("%Y-%m-%d"),
                'company_info': st.session_state.data['company_info'],
                'results': results
            }
            
            # Check if this is a new calculation
            is_new = True
            for historic_data in st.session_state.data.get('history', []):
                if historic_data['date'] == current_data['date']:
                    is_new = False
                    break
            
            if is_new:
                st.session_state.data['history'] = st.session_state.data.get('history', []) + [current_data]
    
    # Display results
    results = st.session_state.data.get('results', {})
    
    if results:
        # Summary
        st.subheader("Emissions Summary")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Create summary metrics
            metrics_cols = st.columns(4)
            
            with metrics_cols[0]:
                st.metric("Total Emissions", f"{results['total_emissions']/1000:.2f} tCO2e")
            
            with metrics_cols[1]:
                st.metric("Scope 1", f"{results['scope1_emissions']/1000:.2f} tCO2e", f"{results['scope1_percentage']:.1f}%")
            
            with metrics_cols[2]:
                st.metric("Scope 2", f"{results['scope2_emissions']/1000:.2f} tCO2e", f"{results['scope2_percentage']:.1f}%")
            
            with metrics_cols[3]:
                st.metric("Scope 3", f"{results['scope3_emissions']/1000:.2f} tCO2e", f"{results['scope3_percentage']:.1f}%")
            
            # Create pie chart
            fig = px.pie(
                values=[results['scope1_emissions'], results['scope2_emissions'], results['scope3_emissions']],
                names=['Scope 1', 'Scope 2', 'Scope 3'],
                title="Emissions by Scope",
                color_discrete_sequence=px.colors.qualitative.G10
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("""
            <div class="highlight">
            <h4>What do these results mean?</h4>
            <p>Your carbon footprint is measured in tonnes of carbon dioxide equivalent (tCO2e), which includes all greenhouse gases converted to the equivalent warming potential of CO2.</p>
            <ul>
                <li><strong>Scope 1:</strong> Direct emissions from owned or controlled sources</li>
                <li><strong>Scope 2:</strong> Indirect emissions from purchased electricity</li>
                <li><strong>Scope 3:</strong> All other indirect emissions in your value chain</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
        
        # Benchmark Comparison
        st.subheader("Benchmark Comparison")
        
        if results.get('benchmark_data'):
            benchmark_data = results['benchmark_data']
            
            st.markdown("""
            <div class="description">
            See how your emissions compare to industry benchmarks. Negative percentages indicate better than average performance.
            </div>
            """, unsafe_allow_html=True)
            
            # Create benchmark visualization
            benchmark_metrics = []
            benchmark_values = []
            benchmark_diffs = []
            
            for metric, values in benchmark_data.items():
                benchmark_metrics.append(metric)
                benchmark_values.append(values['percent_diff'])
                
                if values['percent_diff'] < 0:
                    benchmark_diffs.append('Better than benchmark')
                else:
                    benchmark_diffs.append('Worse than benchmark')
            
            if benchmark_metrics:
                benchmark_df = pd.DataFrame({
                    'Metric': benchmark_metrics,
                    'Percentage Difference': benchmark_values,
                    'Status': benchmark_diffs
                })
                
                fig = px.bar(
                    benchmark_df,
                    x='Metric',
                    y='Percentage Difference',
                    color='Status',
                    title="Comparison with Industry Benchmarks",
                    color_discrete_map={
                        'Better than benchmark': '#2e7d32',
                        'Worse than benchmark': '#c62828'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed benchmark table
                st.markdown("### Detailed Benchmark Comparison")
                
                benchmark_table_data = []
                for metric, values in benchmark_data.items():
                    benchmark_table_data.append({
                        'Metric': metric,
                        'Your Value': f"{values['actual']:.2f}",
                        'Industry Benchmark': f"{values['benchmark']:.2f}",
                        'Difference (%)': f"{values['percent_diff']:.1f}%"
                    })
                
                benchmark_table_df = pd.DataFrame(benchmark_table_data)
                st.dataframe(benchmark_table_df, use_container_width=True)
        else:
            st.info("Benchmark comparison not available for the provided data.")
        
        # Recommendations
        st.subheader("Reduction Recommendations")
        
        if results.get('recommendations'):
            recommendations = results['recommendations']
            
            for recommendation in recommendations:
                st.markdown(f"- {recommendation}")
                
            st.markdown("""
            <div class="highlight">
            <p>These recommendations are tailored to your emissions profile and industry. Implementing them can help reduce your carbon footprint and improve sustainability performance.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Historical Comparison
        if len(st.session_state.data.get('history', [])) > 1:
            st.subheader("Historical Comparison")
            
            # Extract historical data
            dates = []
            emissions = []
            
            for entry in st.session_state.data['history']:
                dates.append(entry['date'])
                emissions.append(entry['results']['total_emissions'] / 1000)  # Convert to tCO2e
            
            # Create line chart
            hist_df = pd.DataFrame({
                'Date': dates,
                'Emissions (tCO2e)': emissions
            })
            
            fig = px.line(
                hist_df,
                x='Date',
                y='Emissions (tCO2e)',
                title="Historical Emissions Trend",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Download Report
        st.subheader("Download Report")
        
        excel_report = create_downloadable_excel(st.session_state.data)
        
        st.markdown(f"""
        <div class="highlight">
        <p>Download a detailed Excel report of your carbon footprint analysis:</p>
        <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{excel_report}" download="carbon_footprint_report.xlsx">
            <button style="background-color: #2e7d32; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer;">
                Download Excel Report
            </button>
        </a>
        </div>
        """, unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("Back to Scope 3", key="results_back"):
            st.session_state.page = 'scope3'
            st.experimental_rerun()
    
    with col3:
        if st.button("Start New Assessment", key="new_assessment"):
            # Reset only the input data, keep history
            history = st.session_state.data.get('history', [])
            st.session_state.data = {
                'company_info': {},
                'scope1': {},
                'scope2': {},
                'scope3': {},
                'results': {},
                'history': history
            }
            st.session_state.page = 'home'
            st.experimental_rerun()

# -------------------------- MAIN APP --------------------------

def main():
    """Main function to run the Streamlit app"""
    # Display sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/150x150.png?text=Carbon+App", width=150)
        st.title("Navigation")
        
        # Navigation links
        if st.button("Home", key="nav_home"):
            st.session_state.page = 'home'
            st.experimental_rerun()
        
        if st.button("Company Information", key="nav_company"):
            st.session_state.page = 'company_info'
            st.experimental_rerun()
        
        if st.button("Scope 1 Emissions", key="nav_scope1"):
            st.session_state.page = 'scope1'
            st.experimental_rerun()
        
        if st.button("Scope 2 Emissions", key="nav_scope2"):
            st.session_state.page = 'scope2'
            st.experimental_rerun()
        
        if st.button("Scope 3 Emissions", key="nav_scope3"):
            st.session_state.page = 'scope3'
            st.experimental_rerun()
        
        if st.button("Results", key="nav_results"):
            st.session_state.page = 'results'
            st.experimental_rerun()
        
        # About section
        st.markdown("---")
        st.markdown("""
        <div class="footer">
        <p>Carbon Footprint Calculator for Indian Companies</p>
        <p>Version 1.0</p>
        <p>Built with Python & Streamlit</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Render the current page
    if st.session_state.page == 'home':
        render_home_page()
    elif st.session_state.page == 'company_info':
        render_company_info_page()
    elif st.session_state.page == 'scope1':
        render_scope1_page()
    elif st.session_state.page == 'scope2':
        render_scope2_page()
    elif st.session_state.page == 'scope3':
        render_scope3_page()
    elif st.session_state.page == 'results':
        render_results_page()

if __name__ == "__main__":
    main()