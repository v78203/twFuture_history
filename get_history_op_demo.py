
# set headers

inputstr = """Accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
Accept-Encoding:gzip, deflate
Accept-Language:zh-TW,zh;q=0.8,en-US;q=0.6,en;q=0.4,zh-CN;q=0.2,ja;q=0.2
Cache-Control:max-age=0
Connection:keep-alive
Content-Length:239
Content-Type:application/x-www-form-urlencoded
Cookie:ASPSESSIONIDCAACQTQB=BIGPDFPDPCPAOMHBIBDDPKCM; AX-cookie-POOL_PORTAL=AFACBAKM; AX-cookie-POOL_PORTAL_web3=ADACBAKM; ASPSESSIONIDACCASQQA=GHPJMAHAJIJGNIPAKKNGAEJI; ASPSESSIONIDACADQRQA=IOPCHONBALLMEKGLLKHFNKDF; ASPSESSIONIDCCDBRQQA=FGBDDKKCKBOMHGBAOKPIKKBO; ASPSESSIONIDQSTQDSTD=HLOCDCEAIKLPJNGKNMEDOLEB; ASPSESSIONIDACAARQRA=APEAPNABEDHDPEHFGCLDBLIO; ASPSESSIONIDQSRSCSTD=PMLFDLKBAPNEANNCABCBOIBF; ASPSESSIONIDAADBACQB=IHLODDNBAIJBFIPOAFIAKFAF; ASPSESSIONIDAAABDDQA=LPMLDGLDHOCOIBCGILAMIKGI; ASPSESSIONIDCCCDACRB=MIHICCIAIFNNIIEOMAHGFEAB; ASPSESSIONIDACDDBCRB=OPHLDPBBNBPDAFCKKEKLOEIK; ASPSESSIONIDCADAACQB=OCHOHNLAKEJLBMICPPLJMGAA
Host:www.taifex.com.tw
Origin:http://www.taifex.com.tw
Referer:http://www.taifex.com.tw/chinese/3/3_2_2.asp
Upgrade-Insecure-Requests:1
User-Agent:Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"""
header = {}
for each in inputstr.split('\n'):
    kv = each.split(':')
    key = kv[0]
    value = ':'.join(kv[1:]) 
    header[key] = value


# set today's date, if it's holiday minus_day let us able to use yesterday's date

def get_day(minus_day):
    import datetime
    today = datetime.datetime.today()- datetime.timedelta(minus_day)
    day = str(today.day)
    month = str(today.month)
    year = str(today.year)
    return [year, month, day]


# set payload to sent to server and get raw data

def get_eachday_table(year, month, day):
    inputstr = """qtype:3
    commodity_id:TXO
    commodity_id2:
    market_code:0
    goday:
    dateaddcnt:-1

    MarketCode:0
    commodity_idt:TXO
    commodity_id2t:
    commodity_id2t2:"""
    payload = {}
    for each in inputstr.split('\n'):
        kv = each.split(':')
        key = kv[0]
        value = ':'.join(kv[1:]) 
        payload[key] = value
    payload['DATA_DATE_Y'] = year
    payload['DATA_DATE_M'] = month
    payload['DATA_DATE_D'] = day
    payload['syear'] = year
    payload['smonth'] = month
    payload['sday'] = day
    payload['datestart'] = year + '/' + month + '/' + day
    import requests
    from bs4 import BeautifulSoup
    res = requests.post('http://www.taifex.com.tw/chinese/3/3_2_2.asp', headers=header ,data = payload)
    res.encoding = 'utf-8'
    import pandas
    df = pandas.read_html(res.text)[2]
    df = df.reindex(df.index.drop(0))
    drop_column = list(range(4,14))
    for i in range(15,19):
        drop_column.append(i)
    drop_column.append(0)
    df = df.drop(df.columns[drop_column],1)
    df.columns = ['week','price','type','volume']
    df = df.dropna() 
    df['volume'] = df['volume'].astype(int)
    weeks = list(df.week.unique())
    types = list(df.type.unique())
    tables = []
    for week in weeks:
        weekdf = df[df['week'].isin([week])]
        for each_type in types:
            tables.append(weekdf[weekdf['type'].isin([each_type])])
    return tables


# from raw data do some cleaning

def get_data():
    tt=0
    while True:
        try:
            today = get_day(tt)
            tables = get_eachday_table(today[0],today[1],today[2])
            tables_today = []
            for table in tables:
                tables_today.append(table.set_index('price'))

            yy = tt+1
            while True:
                try:
                    yesterday = get_day(yy)
                    tables = get_eachday_table(yesterday[0],yesterday[1],yesterday[2])
                    tables_yesterday = []
                    for table in tables:
                        tables_yesterday.append(table.set_index('price'))
                    break
                except IndexError:
                    yy +=1
            break
        except IndexError:
            tt +=1
    return [today, yesterday, tables_today, tables_yesterday]


# the main function to get final data

import numpy as np
data = get_data()
if len(data) != 0:
    (today, yesterday, tables_today, tables_yesterday) = data
    final_tables = []
    for table_today in tables_today:
        find_yesterday = False
        for table_yesterday in tables_yesterday:
            if table_today.week.unique()[0] == table_yesterday.week.unique()[0] and table_today.type.unique()[0] == table_yesterday.type.unique()[0]:
                find_yesterday = True
                table_today['delta'] = (table_today['volume']-table_yesterday['volume'])
                if table_today.isnull().any().any():
                    for each in table_today.index[table_today['delta'].apply(np.isnan)]:
                        table_today.loc[(each),['delta']] = int(table_today.loc[(each),['volume']])
                final_tables.append(table_today)
        if not find_yesterday:
            table_today['delta'] = table_today['volume']
            final_tables.append(table_today)


# from final data do some plot jobs

def plot_and_saving(table1, table2):
    df1 = pandas.DataFrame(table1['volume'])
    df1.columns = ['call volume']
    df1['put volume'] = pandas.DataFrame(table2['volume'])
    df2 = pandas.DataFrame(table1['delta'])
    df2.columns = ['call delta']
    df2['put delta'] = pandas.DataFrame(table2['delta'])

    ax1 = plt.subplot2grid((4, 1), (0, 0), rowspan=3)
    ax2 = plt.subplot2grid((4, 1), (3, 0), rowspan=1)

    plot1 = df1.plot(kind='bar',title=table1.week.unique()[0],figsize=(15,10),mark_right = False ,color=['r','b'],fontsize=13,ax=ax1)
    plot1.get_xaxis().set_visible(False)
    plot1.set_xticklabels([])
    plot2 = df2.plot(kind='bar',color=['r','b'],fontsize=13,ax=ax2)
    # plt.text(60, .025, r'$\mu=100,\ \sigma=15$')
    # plt.axis([40, 160, 0, 0.03])
    title=table1.week.unique()[0]
    # title=final_tables[0].week.unique()[0]

    fileName = "./data/" + "_".join(get_day(0)) + "_" + title
    # plt.show()
    plt.savefig(fileName, bbox_inches='tight')
    plt.close()


# create the data folder to save figures

if __name__ == "__main__":
    import os
    import pandas
    import matplotlib.pyplot as plt
    
    if not os.path.exists("./data"):
        os.makedirs("./data")
    tables = iter(final_tables)
    for table in tables:
        plot_and_saving(table,next(tables))


