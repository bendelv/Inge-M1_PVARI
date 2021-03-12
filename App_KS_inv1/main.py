import pandas as pd
import numpy

import pvlib
import pytz
from pvlib.pvsystem import PVSystem
from pvlib.location import Location

from App_KS_inv1.shadesDetection import *


# Inputs:

# weather.csv with columns named and ordered by
# - date (YYYY-MM-DD HH-MM-SS+DTS; 5min interval)
# - ghi (W/m2)
# - cs_ghi (W/m2)
# - ambtemp (ambient temperature, celsius)
# - windspeed (m/s)

# production.csv with columns named and ordered by
# - date (YYYY-MM-DD HH-MM-SS+DTS; 5min interval)
# - Pdc (power DC, W)
# - Pac (power AC, W)
# OR
# - date (YYYY-MM-DD HH-MM-SS+DTS; 5min interval)
# - Idc (A)
# - Vdc (V)
# - Iac (A)
# - Vac (V)

# location.txt with location information in order
# - latitude, longitude, altitude, locality, timezone

#  installation.txt with hardware installation information
# - surface tilt, surface azimuth, name of inverter, name of modules, number of modules


# Outputs:
# - report on shades identification with periods, angles, estimation of losses. Plots.
# - report on degradation of performance along the years.
# - report on anomaly on the inverters.

def main():
    sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
    sapm_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')

    file = open("installation.txt", "r")
    syst = file.readline().rstrip('\n').split(sep=',')
    syst = [e.strip() for e in syst]
    file.close()

    file = open("location.txt", "r")
    coord = file.readline().rstrip('\n').split(sep=',')
    coord = [e.strip() for e in coord]
    file.close()

    pvsystem = PVSystem(surface_tilt=int(syst[0]),
                        surface_azimuth=int(syst[1]),
                        module_parameters=sandia_modules[syst[2]],
                        inverter_parameters=sapm_inverters[syst[3]],
                        modules_per_string=int(syst[4]))
    pvlocation = Location(latitude=float(coord[0]),
                          longitude=float(coord[1]),
                          altitude=float(coord[2]),
                          tz=pytz.timezone(coord[4]))

    df_prod = pd.read_csv("production.csv")
    if 'Pac' not in df_prod:
        df_prod['Pac'] = df_prod['Iac'] * df_prod['Vac']
    if 'Pdc' not in df_prod:
        if 'Idc' and 'Vdc' in df_prod:
            df_prod['Pdc'] = df_prod['Idc'] * df_prod['Vdc']

    df_weather = pd.read_csv("weather.csv", index_col="date")
    df_weather.index = pd.to_datetime(df_weather.index, utc=True).tz_convert(coord[4])

    # application 1: shade detection and loss estimation
    df_cs = period_cs(df_weather['cs_ghi'], df_weather['ghi'])
    frcst_ac = forecastpv_ac(df_weather, pvlocation, pvsystem)

    print(frcst_ac)

    # application 2: panels degradation

    # application 3: inverter performance (if Pdc available)
    if 'Pdc' not in df:
        print("Power DC is missing, the application cannot calculate inverter performance.")


if __name__ == '__main__':
    main()
