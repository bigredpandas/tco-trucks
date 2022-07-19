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
share_tollable_road = 0.9

################################ CODE #####################################
################################################################################
st.set_page_config(page_title="TCO Comparison Green Trucking", page_icon=None, initial_sidebar_state='expanded')

#caching for better performance
@st.cache
def imports():
    vehicle_cost = pd.read_excel("TCO-trucking.xlsx", sheet_name="Vehicle cost")
    energy_cons = pd.read_excel("TCO-trucking.xlsx", sheet_name="Energy consumption")
    energy_cost = pd.read_excel("TCO-trucking.xlsx", sheet_name="Energy cost")
    eu_country_cost = pd.read_excel("TCO-trucking.xlsx", sheet_name="EU electricity cost", header=11)
    toll_cost = pd.read_excel("TCO-trucking.xlsx", sheet_name="Toll")
    d = {'Year': [2020, 2025, 2030, 2040, 2050], 'Cost [€/t]': [0, 55, 100, 150, 200]}
    co2_price = pd.DataFrame(data=d)
    return vehicle_cost, energy_cons, energy_cost, toll_cost, co2_price, eu_country_cost


vehicle_cost, energy_cons, energy_cost, toll_cost, co2_price_l, eu_country_cost = imports()

cons = energy_cons.copy()
cost = vehicle_cost.copy()
en_cost = energy_cost.copy()
toll = toll_cost.copy()


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
selected_options = st.sidebar.multiselect("Which technologies would you like to compare", ["ICEV","BEV","FCEV","OC-BEV"],["BEV", "FCEV", "ICEV"], format_func=lambda x: options.get(x))
num_options = len(selected_options)


selected_country = st.sidebar.selectbox("Select the country", eu_country_cost["GEO (Labels)"], 14)

selected_price = eu_country_cost.loc[eu_country_cost["GEO (Labels)"] == selected_country, "Electricity price 2019 S-2"].item()
st.sidebar.write('Baseline is Germany, for other countries just electricity prices are updated (tolls, hydrogen price assumed to be same as Germany, which is of course not true)')
selected_year = st.sidebar.select_slider("What year", [2020, 2025, 2030, 2040, 2050], 2025)

st.sidebar.write("Models and assumptions are based on: *Transport & Environment (2021). [How to decarbonise long-haul trucking in Germany. An analysis of available vehicle technologies and their associsated costs.](https://www.transportenvironment.org/wp-content/uploads/2021/07/2021_04_TE_how_to_decarbonise_long_haul_trucking_in_Germany_final.pdf)*")



# main app


container = st.container()
container.title('TCO-Calculator for different Green Trucking Technologies')
eu_country_cost = eu_country_cost.replace(":", 0)


with st.expander("Policy framework", expanded=True):
    co2_price = st.slider("CO2 price [€/CO2-equ. t]", 0, 300, co2_price_l.loc[co2_price_l["Year"] == selected_year, "Cost [€/t]"].item(), 5)

    capex_sub = st.slider("CAPEX subsidy for extra costs in comparison with diesel trucks [% of extra CAPEX subsidized]", 0, 100, 0, 5)/100
    cols = st.columns(num_options)
    for i in range(num_options):
        with cols[i]:
            st.subheader(selected_options[i])
            toll.loc[ (toll["Vehicle"] == selected_options[i]) & (toll["Year"] == selected_year), "Cost [€/km]"] = st.number_input("Toll for infrastructure, noise and air pollution [€/km]", float(0), 0.5, toll_cost.loc[ (toll_cost["Vehicle"] == selected_options[i]) & (toll_cost["Year"] == selected_year), "Cost [€/km]"].item(), 0.01, key="fsdp"+str(i))

container2 = st.container()

with st.expander("Vehicle Cost"):
    num_years = st.slider("Period under observation [years]", 1, 5, 5, 1)
    res_value = st.slider("Residual value after observation period [% of purchase costs]", 0, 100,
                          int(100 - (75 / 5 * num_years)), 1) / 100
    cols = st.columns(num_options)
    for i in range(num_options):
        with cols[i]:
            st.subheader(selected_options[i])
            cost.loc[ (cost["Vehicle"] == selected_options[i]) & (cost["Cost type"] == "Purchase cost") & (cost["Year"] == selected_year), "Cost [€]"] = st.number_input("Purchase cost [t€]", float(50), float(1000), vehicle_cost.loc[ (vehicle_cost["Vehicle"] == selected_options[i]) & (vehicle_cost["Cost type"] == "Purchase cost") & (vehicle_cost["Year"] == selected_year), "Cost [€]"].item()/1000, float(10), key="vp"+str(i))*1000*(1-res_value)

            cost.loc[ (cost["Vehicle"] == selected_options[i]) & (cost["Cost type"] == "Maintenance & repair") & (cost["Year"] == selected_year), "Cost [€]"] = st.number_input("Annual maintenance & repair [t€]", float(2), float(1000), vehicle_cost.loc[ (vehicle_cost["Vehicle"] == selected_options[i]) & (vehicle_cost["Cost type"] == "Maintenance & repair")& (vehicle_cost["Year"] == selected_year), "Cost [€]"].item()/1000, float(1), key="vm"+str(i)) * 1000


with st.expander("Vehicle Energy Consumption"):
    yearly_mileage = st.slider("Average annual mileage [km]", 10000, 300000,  136750, 5000)
    cols = st.columns(num_options)
    st.markdown("All values tank/plug to wheel")
    for i in range(num_options):
        with cols[i]:

            st.subheader(selected_options[i])
            cons.loc[(cons["Vehicle"] == selected_options[i]) & (cons["Year"] == selected_year), "Consumption"] = st.number_input("Energy consumption [" + energy_cons.loc[(energy_cons["Vehicle"] == selected_options[i]) & (energy_cons["Year"] == selected_year), "Unit"].item() + "]", float(0), float(50), energy_cons.loc[(energy_cons["Vehicle"] == selected_options[i]) & (energy_cons["Year"] == selected_year), "Consumption"].item(), float(0.025))

            # for diesel l/100 km needs to be converted to kWh/km
            if cons.loc[(cons["Vehicle"] == selected_options[i]) & (cons["Year"] == selected_year), "Unit"].item() == "l/100 km":

                cons.loc[(cons["Vehicle"] == selected_options[i]) & (cons["Year"] == selected_year), "Consumption"] = cons.loc[(cons["Vehicle"] == selected_options[i]) & (cons["Year"] == selected_year), "Consumption"] / 100 * col_value_diesel

                cons.loc[(cons["Vehicle"] == selected_options[i]) & (cons["Year"] == selected_year), "Unit"] = "kWh/km"



with container2.expander("Energy Cost"):
    cols = st.columns(num_options)
    for i in range(num_options):
        with cols[i]:
            st.subheader(selected_options[i])
            if (selected_options[i] == "BEV" or selected_options[i] == "OC-BEV") and selected_country != "Germany":
                en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"] = st.number_input("Energy/fuel cost [€/kWh]", float(0), float(1), selected_price, 0.01, key="ectg"+str(i))
            else:
                en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"] = st.number_input("Energy/fuel cost [" + energy_cost.loc[(energy_cost["Vehicle"] == selected_options[i]) & (energy_cost["Year"] == selected_year), "Unit"].item() + "]", float(0), float(10), energy_cost.loc[(energy_cost["Vehicle"] == selected_options[i]) & (energy_cost["Year"] == selected_year), "Cost"].item(), 0.025, key="ec"+str(i))

            if en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Unit"].item() == "€/l Diesel":

                en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"] = en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"].item() / col_value_diesel

            elif en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Unit"].item() == "€/kg H2":

                en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"] = en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"].item() / energy_density_h2

        cost.loc[(cost["Vehicle"] == selected_options[i]) & (cost["Cost type"] == "Fuel/Electricity") & (cost["Year"] == selected_year), "Cost [€]"] = cons.loc[(cons["Vehicle"] == selected_options[i]) & (cons["Year"] == selected_year), "Consumption"].item() * en_cost.loc[(en_cost["Vehicle"] == selected_options[i]) & (en_cost["Year"] == selected_year), "Cost"].item() * yearly_mileage

    cost.loc[(cost["Cost type"] == "CO2 price") & (cost["Year"] == selected_year) & (cost["Vehicle"] == "ICEV"), "Cost [€]"] = cons.loc[(cons["Vehicle"] == "ICEV") & (cons["Year"] == selected_year), "Consumption"].item() * yearly_mileage * co2_em_diesel * co2_price / 1000




with st.expander("Infrastructure Cost"):
    cols = st.columns(num_options)
    for i in range(num_options):
        with cols[i]:
            st.subheader(selected_options[i])
            cost.loc[ (cost["Vehicle"] == selected_options[i]) & (cost["Cost type"] == "Infrastructure") & (cost["Year"] == selected_year), "Cost [€]"] = st.number_input("Annual infrastructure cost [t€]", float(0), float(1000), vehicle_cost.loc[ (vehicle_cost["Vehicle"] == selected_options[i]) & (vehicle_cost["Cost type"] == "Infrastructure") & (vehicle_cost["Year"] == selected_year), "Cost [€]"].item()/1000, float(1), key="vpgg"+str(i))*1000

# Toll cost calculation
for i in range(num_options):
    cost.loc[ (cost["Vehicle"] == selected_options[i]) & (cost["Cost type"] == "Toll") & (cost["Year"] == selected_year), "Cost [€]"] = toll.loc[ (toll["Vehicle"] == selected_options[i]) & (toll["Year"] == selected_year), "Cost [€/km]"].item() * share_tollable_road * yearly_mileage


cost.loc[cost["Recurring annual cost"] == True, "Cost [€]"] = cost.loc[cost["Recurring annual cost"] == True, "Cost [€]"] * num_years

# CAPEX subsidy calculation
buffer = selected_options.copy()
if "ICEV" in buffer:
    buffer.remove("ICEV")

for i in range(len(buffer)):
    cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Subsidy") & (cost["Year"] == selected_year), "Cost [€]"] = (cost.loc[(cost["Vehicle"] == "ICEV") & (cost["Cost type"] == "Purchase cost") & (cost["Year"] == selected_year), "Cost [€]"].item() - (cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Purchase cost") & (cost["Year"] == selected_year), "Cost [€]"].item() + cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Infrastructure") & (cost["Year"] == selected_year), "Cost [€]"].item())) * capex_sub

    if cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Subsidy") & (cost["Year"] == selected_year), "Cost [€]"].item() > 0:
        cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Subsidy") & (cost["Year"] == selected_year), "Cost [€]"] = 0

    #if infrastructure cost times subsidy share is greater than total subsidy then
    if -cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Subsidy") & (cost["Year"] == selected_year), "Cost [€]"].item() > cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Infrastructure") & (cost["Year"] == selected_year), "Cost [€]"].item() * capex_sub:
        #
        cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Purchase cost") & (cost["Year"] == selected_year), "Cost [€]"] = cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Purchase cost") & (cost["Year"] == selected_year), "Cost [€]"].item() + cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Subsidy") & (cost["Year"] == selected_year), "Cost [€]"].item() + cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Infrastructure") & (cost["Year"] == selected_year), "Cost [€]"].item() * capex_sub

        cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Infrastructure") & (cost["Year"] == selected_year), "Cost [€]"] = cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Infrastructure") & (cost["Year"] == selected_year), "Cost [€]"].item() * (1 - capex_sub)
    else:
        cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Infrastructure") & (cost["Year"] == selected_year), "Cost [€]"] = cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Infrastructure") & (cost["Year"] == selected_year), "Cost [€]"].item() + cost.loc[(cost["Vehicle"] == buffer[i]) & (cost["Cost type"] == "Subsidy") & (cost["Year"] == selected_year), "Cost [€]"].item()

#calculate percentage
cost_e = cost.copy().groupby(["Vehicle", "Cost type","Year","Recurring annual cost","Class"]).agg({"Cost [€]":"sum"})
cost_e["Share of TCO"] = cost_e.groupby(["Vehicle","Year","Class"]).apply(lambda x:
                                                 100 * x / float(x.sum())).values
cost_e["Share of TCO"] = cost_e["Share of TCO"].astype(int).apply(str) + "%"
cost_e.reset_index(inplace=True)


cost = cost_e
cost = cost.loc[(cost["Year"] == selected_year) & (cost["Vehicle"].isin(selected_options))]
cost["Cost type"] = cost["Cost type"].replace({'Purchase cost':'Vehicle'})
fig = px.bar(cost, x="Vehicle", y="Cost [€]",  color="Cost type",  hover_name="Vehicle", hover_data= ["Share of TCO"],color_discrete_sequence=px.colors.qualitative.T10, title="Total cost of ownership 40 ton truck in first "+str(num_years)+" year use period<br><sup>Base year "+str(selected_year) +", " + str(yearly_mileage)+ " km yearly mileage, excluding driver costs</sup>")

fig.update_xaxes(categoryorder='array', categoryarray= selected_options)
fig.update_layout(font_size = 15, title_x=0.5)

# out of order displaying with containers
container.write(fig)

st.subheader("Sources")
st.markdown("Eurostat (2021). [Electricity prices for non-household consumers - bi-annual data (from 2007 onwards)](https://ec.europa.eu/eurostat/databrowser/view/NRG_PC_205__custom_1376243/default/table?lang=en)\n\nWorldbank (2021). [Carbon Pricing Dashboard](https://carbonpricingdashboard.worldbank.org)\n\nTransport & Environment (2021). [How to decarbonise long-haul trucking in Germany. An analysis of available vehicle technologies and their associsated costs.](https://www.transportenvironment.org/wp-content/uploads/2021/07/2021_04_TE_how_to_decarbonise_long_haul_trucking_in_Germany_final.pdf)")

