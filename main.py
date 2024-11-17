import requests
import os
import pandas as pd
import gspread
import numpy as np
from collections import Counter



#specify form id from the server
formid='gage_endline_cr_survey'
#the csv file downloaded has name= formid+_WIDE that is why
out_put=f'{formid}_WIDE'

#specify server name eg laterite, tnscieame, etc
server='laterite'

#surveycto username and password
username='bgetachew@laterite.com'
password=os.getenv("PASSWORD")

ok=requests.get(f'https://{server}.surveycto.com/api/v2/forms/data/wide/json/{formid}?date=0', auth=(username, password))

data=pd.DataFrame(ok.json())



gc=gspread.service_account(filename='credentials.json')
key_='1pYvRBSIFVFtjhor7qUynL9ogTfZcF6JyC9NS7Blu10k'
sh=gc.open_by_key(key_)

### global common variables
var_list=['starttime', 'cs_supervname_name', 'cs_enumname_name', 'hhid', 'KEY']

### READIN IN THE CONTROL SHEET
ctr=sh.worksheet('CONTROL')
ctr_val=ctr.cell(1, 1).value
print(ctr_val)

### READING IN THE DATA QUALITY SHEET
dq=sh.worksheet('Data Quality - General')
data_csv=data

print(data.shape)
### Keeping only the most uptodate data to monitor
data=data[data['SubmissionDate']>ctr_val]
# print(data.shape)

def data_quality_checks(data):
    ### check 1 Dwellin versus number of people living in the household
    ### dw_roomnum/(hhr_adultnum + hhr_childnum)
    data2=data
    data2['dw_roomnum']=data2['dw_roomnum'].astype(float)
    data2=data2[data2['dw_roomnum'] != '']
    data2=data2[data2['dw_roomnum'] != 'nan']
    data2['dw_roomnum'].dropna()
    data2['hhr_adultnum']=data2['hhr_adultnum'].astype(float)
    data2['hhr_childnum']=data2['hhr_childnum'].astype(float)
    data2['rooms_over_people']=data2['dw_roomnum']/(data2['hhr_adultnum']+data2['hhr_childnum'])
    data2['var']='dw_roomnum'
    data2['dw_roomnum']=data2['dw_roomnum'].astype(str)
    data2['hhr_adultnum']=data2['hhr_adultnum'].astype(str)
    data2['hhr_childnum']=data2['hhr_childnum'].astype(str)
    data2['comment']= data2['dw_roomnum'] + " number of rooms in a house with " + data2['hhr_adultnum']+" adults and " + data2['hhr_childnum']+ " children. Confirm."
    data2['rooms_over_people']=data2['rooms_over_people'].astype(float)
    Q1 = float(data2['rooms_over_people'].quantile(0.25))
    Q3 = float(data2['rooms_over_people'].quantile(0.75))
    rooms=data2[(data2['rooms_over_people']<Q1)]
    rooms=rooms[var_list+['var', 'comment']]
    dq.append_rows(rooms.values.tolist())


    #### Check 2 Toilet shared with more than 10 people
    data3=data
    data3=data3[data3['dw_toiletshare']==3]
    data3['var']='dw_toiletshare'
    data3['comment']="Household shares toilet with 10/more people confirm!"
    dq.append_rows(data3[var_list+['var', 'comment']].values.tolist())


    ### Check 3 AND 4 paid amount versus hours worked past 7 days and typical 
    if 'pw_10_1' in data.columns:
        data4=data
        data4=data4[data4['pw_10_1'] != '']
        data4=data4[data4['pw_10_1'] != 'nan']
        print("dfdf'")
        data4['pay_per_week_now']=data4['pw_10_1']/data4['pw_9_1']
        Q1= float(data4['pay_per_week_now'].quantile(0.25))
        Q3= float(data4['pay_per_week_now'].quantile(0.25))
        data4['var']='pw_10_1'
        data4['comment']="CR paid "+ data4['pw10_1'] + " working for "+ data4['pw_9_1']+" hours. Confirm!"
        data4=data4[(data4['pay_per_week_now']<Q1) & data4['pay_per_week']>Q3]
        dq.append_rows(data4[var_list+['var', 'comment']].values.tolist())

    data5=data
    if 'pw_10a_1' in data.columns:
        data5=data5[data5['pw_10a_1'] != '']
        data5=data5[data5['pw_10a_1'] != 'nan']
        data5['pay_per_week_nowa']=data5['pw_10a_1']/data5['pw_9a_1']
        Q1= float(data5['pay_per_week_nowa'].quantile(0.25))
        Q3= float(data5['pay_per_week_nowa'].quantile(0.25))
        data5['var']='pw_10a_1'
        data5['comment']="CR is typically paid "+ data5['pw10a_1'] + " working for "+ data5['pw_9a_1']+" hours. Confirm!"
        data5=data5[(data5['pay_per_week_nowa']<Q1) & data5['pay_per_week_nowa']>Q3]
        dq.append_rows(data5[var_list+['var', 'comment']].values.tolist())


if data.shape[0]>0:
    max=data['SubmissionDate'].max()
    ctr.update_cell(1, 1, max)
    data_quality_checks(data)