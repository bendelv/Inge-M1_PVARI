import numpy as np
import pandas as pd

import pvlib
from pvlib.modelchain import ModelChain


def forecastpv_ac(dfw, pvloc, pvsyst):

    ephemeris = pvlib.solarposition.ephemeris(dfw.index, pvloc.latitude, pvloc.longitude, pressure=101325,
                                              temperature=dfw.ambtemp.values)
    erbs = pvlib.irradiance.erbs(dfw.ghi.values, ephemeris['zenith'], dfw.index.dayofyear)

    dni = erbs['dni']
    # Max DNI in BELGIUM = 1000
    dni[dni > 1000] = 1000
    dhi = erbs['dhi']

    data = {
        'ghi': dfw.ghi.values,
        'dhi': dhi,
        'dni': dni,
        'temp_air': dfw.ambtemp.values,
        'wind_speed': dfw.windspeed.values
    }
    weather = pd.DataFrame(data, index=dfw.index)

    mc = ModelChain(pvsyst, pvloc, spectral_model='no_loss')

    mc.run_model(times=weather.index, weather=weather)
    mc.ac.rename("frcst_ac", inplace=True)
    return mc.ac


# input:
# - s_cs: clear sky irradiance time series
# - s_ghi: measured ghi time series (same dates, freq as dfcs)
def period_cs(s_cs, s_ghi):
    # remove rows where theoric clearsky ghi is null, causing loss being close to 0.
    s_ghi = s_ghi[s_cs >= 50]
    s_cs = s_cs[s_cs >= 50]
    loss_cs = (s_cs - s_ghi).abs()

    # reject ClearSky assumption if loss is sup to 0.1*theoric ghi (in t)
    dev = 0.1
    thresh = dev * s_cs

    pcs = s_ghi[loss_cs <= thresh]
    print(pcs.index[0]+pd.DateOffset(hours=2))
    print(pcs.all(pcs.index[0] < pcs.index < pcs.index[0] + pd.DateOffset(hours=2)))

    #for i in pcs.iteritems():
        #btw = pcs.between_time(i.index, i.index+pd.DateOffset(hours=2))

    # KEEP SEQ OF LENGTH SUPERIOR TO 2H -------------------------------------------------------------------------------
    sem = 0
    seqs = []
    seq = []

    for index, row in df.iterrows():
        if row['deviated'] == 0:
            seq.append(index)
            sem = 1
        else:
            if sem == 1:
                if len(seq) >= 24:
                    seqs.extend(seq)
                sem = 0
                seq = []
    return seqs


def error_detection(df_csperiods, timezone, plot=False):
    df = df_csperiods
    # LOSS PROD/FORECAST ----------------------------------------------------------------------------------------------
    df['loss'] = np.select(
        [
            df.frcst_ac - df.prod_ac > 0,
            df.frcst_ac - df.prod_ac <= 0
        ],
        [
            df.frcst_ac - df.prod_ac,
            0
        ]
    )

    df['loss_rate'] = df['loss'] / df['frcst_ac']
    df['rolMean_loss'] = df['loss_rate'].rolling(window=3, center=True).mean()

    thresh = 0.2
    df['error'] = np.select(
        [
            df['rolMean_loss'] <= thresh,
            df['rolMean_loss'] > thresh
        ],
        [
            0,
            1
        ]
    )

    # filters cs periods with errors
    df = df[df['error'] == 1]

    # Set time to local time zone and aggregate
    df.index = df.index.tz_convert(timezone)
    mthsErr_mean = df.groupby([df.index.month, df.index.hour, df.index.minute])['loss'].mean()
    mthsErr_mean.index.names = ['month', 'hour', 'minute']

    mthsErr_count = df.groupby([df.index.month, df.index.hour, df.index.minute])['loss'].count()
    mthsErr_count.index.names = ['month', 'hour', 'minute']

    mthsErr = pd.merge(mthsErr_mean, mthsErr_count, on=['month', 'hour', 'minute'], how='left')
    mthsErr.rename(columns={'loss_x': 'loss', 'loss_y': 'count'}, inplace=True)

