# -*- coding: utf-8 -*-
"""
Created on 18 September 2021

@author: Jan Biederbeck
"""
################################### IMPORTS ####################################
################################################################################
import pandas as pd
import numpy as np
import streamlit as st
from PIL import Image
import copy
import os
import plotly.express as px

################################ MODUL-IMPORTS #################################
################################################################################

################################ FUNCTIONS #####################################
################################################################################

col_value_diesel = 9.921 # kWh/l -> There is Brennwert and Heizwert, depending on the scope
co2_em_diesel = 2.65 / col_value_diesel # kg CO2 / kWh  https://www.helmholtz.de/erde-und-umwelt/wie-viel-co2-steckt-in-einem-liter-benzin/ 2.65 kg Co2/l Diesel
energy_density_h2 = 33.33 #kWh/kg


################################ CODE #####################################
################################################################################
st.set_page_config(page_title=None, page_icon=None, layout='wide', initial_sidebar_state='expanded')

vehicle_cost = pd.read_excel("TCO-trucking.xlsx", sheet_name="Vehicle cost")
energy_cons = pd.read_excel("TCO-trucking.xlsx", sheet_name="Energy consumption")
energy_cost = pd.read_excel("TCO-trucking.xlsx", sheet_name="Energy cost")

cons = energy_cons.copy()
cost = vehicle_cost.copy()
en_cost = energy_cost.copy()

options = {
    "ICEV" : "Internal combustion engine w/ Diesel (ICEV)",
    "BEV" : "Battery-electric (BEV)",
    "FCEV" : "Fuel-cell (FCEV)",
    "OC-BEV" : "Battery electric w/ overhead catenary infrastructure (OC-BEV)"
    }

purchase_cost = {}
m_r_cost = {}


# here starts the web interface

#sidebar
st.sidebar.title('Pre-Settings')
selected_options = st.sidebar.multiselect("Which technologies would you like to compare", ["ICEV","BEV","FCEV","OC-BEV"],["BEV", "FCEV"], format_func=lambda x: options.get(x))
num_options = len(selected_options)

st.sidebar.checkbox("Expert mode")

selected_weight = st.sidebar.select_slider("Which class of vehicle (metric tons)", [10, 20, 40], 40)

selected_year = st.sidebar.select_slider("What year", [2020, 2025, 2030, 2040, 2050], 2025)

st.sidebar.write("Models and assumptions for long-haul trucks (40 t) are based on: *Transport & Environment (2021). [How to decarbonise long-haul trucking in Germany. An analysis of available vehicle technologies and their associsated costs.](https://www.transportenvironment.org/wp-content/uploads/2021/07/2021_04_TE_how_to_decarbonise_long_haul_trucking_in_Germany_final.pdf)*  \n\n Assumptions for 22 and 7.5 t vehicles are based on market feedback\n\nFor Feeback hit me up on [LinkedIn](https://www.linkedin.com/in/jan-biederbeck/) or email (trucks@jan-biederbeck.de).  \n Source Code can be found on [GitHub](https://github.com/bigredpandas/tco-trucks).")



# main app
st.write(cost.loc[vehicle_cost["Year"] == selected_year])

container = st.container()
container.title('TCO-Calculator for different Green Trucking Technologies')

with st.expander("Policy framework", expanded=True):
    co2_price = st.slider("CO2 price [€/CO2-equ. t]", 0, 300, 50, 5)
    capex_sub = st.slider("CAPEX subsidy for extra costs in comparison with diesel trucks [% of extra CAPEX subsidized]", 0, 100, 80, 5)

with st.expander("Vehicle Cost"):
    cols = st.columns(num_options)
    for i in range(num_options):
        with cols[i]:
            st.header(selected_options[i])
            cost.loc[ (cost["Vehicle"] == selected_options[i]) & (cost["Cost type"] == "Purchase cost") & (cost["Year"] == selected_year), "Cost [€]"] = st.number_input("Purchase cost in t€", float(50), float(1000), vehicle_cost.loc[ (vehicle_cost["Vehicle"] == selected_options[i]) & (vehicle_cost["Cost type"] == "Purchase cost") & (vehicle_cost["Year"] == selected_year), "Cost [€]"].item()/1000, float(10), key="vp"+str(i))*1000

            cost.loc[ (cost["Vehicle"] == selected_options[i]) & (cost["Cost type"] == "Maintenance & repair") & (cost["Year"] == selected_year), "Cost [€]"] = st.number_input("Annual maintenance & repair in t€", float(2), float(1000), vehicle_cost.loc[ (vehicle_cost["Vehicle"] == selected_options[i]) & (vehicle_cost["Cost type"] == "Maintenance & repair")& (vehicle_cost["Year"] == selected_year), "Cost [€]"].item()/1000, float(1), key="vm"+str(i)) * 1000


st.write(cost.loc[vehicle_cost["Year"] == selected_year])

with st.expander("Vehicle Stats & Energy Consumption"):
    num_years = st.slider("Period under observation [years]", 1, 20, 5, 1)
    yearly_mileage = st.slider("Average anual mileage [km]", 10000, 300000,  136750, 5000)
    cols = st.columns(num_options)
    for i in range(num_options):
        with cols[i]:
            st.header(selected_options[i])
            cons.loc[(cons["Vehicle"] == selected_options[i]) & (cons["Year"] == selected_year), "Consumption"] = st.number_input("Energy consumption [" + energy_cons.loc[(energy_cons["Vehicle"] == selected_options[i]) & (energy_cons["Year"] == selected_year), "Unit"].item() + "]", float(0), float(50), energy_cons.loc[(energy_cons["Vehicle"] == selected_options[i]) & (energy_cons["Year"] == selected_year), "Consumption"].item(), float(0.025))

            # for diesel l/100 km needs to be converted to kWh/km
            if cons.loc[(cons["Vehicle"] == selected_options[i]) & (cons["Year"] == selected_year), "Unit"].item() == "l/100 km":

                cons.loc[(cons["Vehicle"] == selected_options[i]) & (cons["Year"] == selected_year), "Consumption"] = cons.loc[(cons["Vehicle"] == selected_options[i]) & (cons["Year"] == selected_year), "Consumption"] / 100 * col_value_diesel

                cons.loc[(cons["Vehicle"] == selected_options[i]) & (cons["Year"] == selected_year), "Unit"] = "kWh/km"


with st.expander("Energy Cost"):
    cols = st.columns(num_options)
    for i in range(num_options):
        with cols[i]:
            st.header(selected_options[i])
            en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"] = st.number_input("Energy/fuel cost [" + energy_cost.loc[(energy_cost["Vehicle"] == selected_options[i]) & (energy_cost["Year"] == selected_year), "Unit"].item() + "]", float(0), float(10), energy_cost.loc[(energy_cost["Vehicle"] == selected_options[i]) & (energy_cost["Year"] == selected_year), "Cost"].item(), 0.025, key="ec"+str(i))

            if en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Unit"].item() == "€/l Diesel":

                en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"] = en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"].item() / col_value_diesel

            elif en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Unit"].item() == "€/kg H2":

                en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"] = en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"].item() / energy_density_h2

        cost.loc[(cost["Vehicle"] == selected_options[i]) & (cost["Cost type"] == "Fuel") & (cost["Year"] == selected_year), "Cost [€]"] = cons.loc[(cons["Vehicle"] == selected_options[i]) & (cons["Year"] == selected_year), "Consumption"].item() * en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"].item() * yearly_mileage

    cost.loc[(cost["Cost type"] == "CO2 price") & (cost["Year"] == selected_year) & (cost["Vehicle"] == "ICEV"), "Cost [€]"] = cons.loc[(cons["Vehicle"] == "ICEV") & (cons["Year"] == selected_year), "Consumption"].item() * yearly_mileage * co2_em_diesel * co2_price / 1000




with st.expander("Infrastructure Cost"):
    col1, col2, col3 = st.columns(3)
    st.write("test")

#for i in range(num_options):
    # für jede alternative

#cost.loc[(cost["Cost type"] == "Fuel") & (cost["Year"] == selected_year), "Cost [€]"] = cost.loc[(cost["Cost type"] == "Fuel") & (cost["Year"] == selected_year), "Cost [€]"] *

cost.loc[cost["Recurring annual cost"] == True, "Cost [€]"] = cost.loc[cost["Recurring annual cost"] == True, "Cost [€]"] * num_years
cost = cost.loc[cost["Vehicle"].isin(selected_options)]
fig = px.bar(cost.loc[vehicle_cost["Year"] == selected_year], x="Vehicle", y="Cost [€]", color="Cost type")
fig.update_xaxes(categoryorder='array', categoryarray= selected_options)
st.write(cost.loc[vehicle_cost["Year"] == selected_year])
# out of order displaying with containers
container.write(fig)
