from    time                    import  sleep
from    datetime                import  datetime    , timedelta
from    dateutil.relativedelta  import  relativedelta

import saltools.misc    as      sltm
import logging
import pandas           as      pd
import numpy            as      np
import traceback, re
import time

TIME_FRAMES = [
    'Hourly'    , 
    'Daily'     , 
    'Weekly'    , 
    'Monthly'   ]
ALL_TABLES  = [
    'min_5min'  ,
    'min_15min' ,
    'min_60min' ,
    'day_1day'  ,
    'day_1W'    ,
    'day_1M'    ]
FREQUENCIES = [
    'Once'      , 
    'Daily'     ,
    'Hourly'    ,
    'Minutes'   ]
DIRECTIONS  = [
    'Short'         , 
    'Long'          ,
    'Short+Long'    ]


def parseCSV(file):
    data = pd.read_csv(file) 
    return data


class ExceptionNoZoneFound(Exception):
    def __init__(
        self        ,
        zone_type   ):
        self.message = 'No {} zone was found for the given parameters'.format(zone_type)


# Import DataFrame in program, where each Row is a class Candle
# After that we have a list of class Candles with range equal to (GUI5) 
# Feeding that list to class Range ( htf = Range())
class Candle():
    # Initializing 
    def __init__(self, dfRow, params):
        self.params   = params
        self.date     = dfRow[1]['Date']
        self.open     = float(dfRow[1]['Open'])
        self.close    = float(dfRow[1]['Close'])
        self.high     = float(dfRow[1]['High'])
        self.low      = float(dfRow[1]['Low'])
        self.body     = abs(self.open - self.close)
        self.range    = abs(self.high - self.low)
        self.b2r      = self.body / self.range
        #self.volume   = dfRow[1]['Volume']
        self.DZgap    = 0  # DZGap is added ont op of current body
        self.SZgap    = 0  # SZGap is added right under current body
        self.type     = 'none'
        # Gap is body

        if self.open > self.close: self.color = 'red'
        else: self.color = 'green'

    # Deleting (Calling destructor) 
    def __del__(self): 
        # Free up memory 
        pass

    def getSpecs(self):
        # Debug
        #print("Candle")
        #print(self.date)
        #print(self.DZgap)
        #print(self.SZgap)
        #print("End\n")
        # Debug

        # Body with Gap
        self.bodywithgap     = abs(self.open - self.close) + self.DZgap + self.SZgap
        self.bodywithgap2r   = self.bodywithgap / self.range
        


# The area of tickers (GUI 5) we are looking at
# Candle List is importd here to calculate area-specific parameters
class Area():

    def __init__(self, clist, params, logging):

        self.logging = logging
        self.params = params
        self.lowNow  = clist[0].low
        self.highNow = clist[0].high
        self.clist   = clist

        # Iterate all candles and find the Gaps
        for i in range(0, len(clist)):
            
            try:
                # Long trade Gap
                if max(self.clist[i].open, self.clist[i].close) > self.clist[i+1].high and self.clist[i].low > self.clist[i+1].high:
                    if clist[i].b2r > clist[i+1].b2r:
                        clist[i].DZgap = clist[i].DZgap + abs(self.clist[i].low - self.clist[i+1].high)
                    else:
                        clist[i+1].DZgap = clist[i+1].DZgap + abs(self.clist[i].low - self.clist[i+1].high)
                # Short trade Gap
                if min(self.clist[i].open, self.clist[i].close) < self.clist[i+1].low and self.clist[i].high < self.clist[i+1].low:
                    if clist[i].b2r > clist[i+1].b2r:
                        clist[i].SZgap = clist[i].SZgap + abs(self.clist[i+1].low - self.clist[i].high)
                    else:
                        clist[i+1].SZgap = clist[i+1].SZgap + abs(self.clist[i+1].low - self.clist[i].high)
                
                clist[i].getSpecs()
            except IndexError as e:
                # Reached EOF: Next candle after this one is EOF
                clist[i].getSpecs()
                logging.info("\t+ End of {}-candle DataFrame, last date is {}\n".format(i, clist[i].date))


    def __del__(self):
        pass


    def topX(self, X):
        bodies = []
        for cl in self.clist:
            bodies.append(cl.body)
        bodies.sort()
        
        return bodies[X-1]


    def scanCircle(self, direction):

        Now = self.clist[0]
        Lowest = self.lowNow
        Highest = self.highNow

        for i in range(0, len(self.clist)-1):

            Lowest = min(Lowest, self.clist[i].low)
            Highest = max(Highest, self.clist[i].high)

            # STEP 1
            if direction == 'Long':
                if self.clist[i+1].open < self.lowNow and self.clist[i+1].open < Lowest and self.clist[i+1].color == 'green' and self.clist[i+1].body >= self.topX(int(self.params['loX'])):
                    # Debug
                    #print("-----")
                    #print(float(self.params['loDZr']))
                    #print("Bratio: ", self.clist[i+1].b2r)
                    #print(self.clist[i+1].date)
                    #print("Lowest: ", Lowest)
                    #print("Open: ", self.clist[i+1].open)
                    # Debug 

                    # Possible Leg-out check further
                    # if its a leg-out indeed proceed
                    if self.clist[i+1].bodywithgap2r  >= float(self.params['loDZr']):
                        
                        # STEP 2
                        if self.clist[i+2].b2r <= float(self.params['bDZr']):
                            
                            # STEP 3
                            if self.clist[i+3].bodywithgap2r >= float(self.params['liDZr']):
                                ZoneTop = self.clist[i+2].open
                                ZoneBot = min(self.clist[i+1].low, self.clist[i+2].low)
                                pattern_end = 3
                                break

                            elif self.clist[i+3].b2r <= float(self.params['bDZr']):
                                
                                # STEP 4
                                if self.clist[i+4].bodywithgap2r >= float(self.params['liDZr']):
                                    ZoneTop = max(self.clist[i+2].open, self.clist[i+3].open)
                                    ZoneBot = min(self.clist[i+1].low, self.clist[i+2].low, self.clist[i+3].low)
                                    pattern_end = 4
                                    break

                                elif self.clist[i+4].b2r <= float(self.params['bDZr']):

                                    # STEP 5
                                    if self.clist[i+5].bodywithgap2r >= float(self.params['liDZr']):
                                        ZoneTop = max(self.clist[i+2].open, self.clist[i+3].open, self.clist[i+4].open)
                                        ZoneBot = min(self.clist[i+1].low, self.clist[i+2].low, self.clist[i+3].low, self.clist[i+4].low)
                                        pattern_end = 5
                                        break
                                    else:
                                        continue

                                else:
                                    continue

                            else:
                                continue

                        else:
                            continue



            elif direction == 'Short':
                if self.clist[i+1].open > self.highNow and self.clist[i+1].open > Highest and self.clist[i+1].color == 'red' and self.clist[i+1].body >= self.topX(int(self.params['loX'])):
                    # Debug
                    #print("-----")
                    #print(float(self.params['loSZr']))
                    #print("Bratio: ", self.clist[i+1].b2r)
                    #print(self.clist[i+1].date)
                    #print("Highest: ", Highest)
                    #print("Open: ", self.clist[i+1].open)
                    # Debug

                    # Possible Leg-out check further
                    # if its a leg-out indeed proceed
                    if self.clist[i+1].bodywithgap2r  >= float(self.params['loSZr']):
                        
                        # STEP 2
                        if self.clist[i+2].b2r <= float(self.params['bSZr']):

                            # STEP 3
                            if self.clist[i+3].bodywithgap2r >= float(self.params['liSZr']):
                                ZoneBot = self.clist[i+2].close
                                ZoneTop = max(self.clist[i+1].high, self.clist[i+2].high)
                                pattern_end = 3
                                break

                            elif self.clist[i+3].b2r <= float(self.params['bSZr']):
                                
                                # STEP 4
                                if self.clist[i+4].bodywithgap2r >= float(self.params['liSZr']):
                                    ZoneBot = min(self.clist[i+2].close, self.clist[i+3].close)
                                    ZoneTop = min(self.clist[i+1].high, self.clist[i+2].high, self.clist[i+3].high)
                                    pattern_end = 4
                                    break

                                elif self.clist[i+4].b2r <= float(self.params['bSZr']):

                                    # STEP 5
                                    if self.clist[i+5].bodywithgap2r >= float(self.params['liSZr']):
                                        ZoneBot = min(self.clist[i+2].close, self.clist[i+3].close, self.clist[i+4].close)
                                        ZoneTop = min(self.clist[i+1].high, self.clist[i+2].high, self.clist[i+3].high, self.clist[i+4].high)
                                        pattern_end = 5
                                        break
                                    else:
                                        continue

                                else:
                                    continue

                            else:
                                continue

                        else:
                            continue


        try:
            if ZoneBot and ZoneTop:
                return self.clist[i+1].date, self.clist[i+pattern_end].date, ZoneBot, ZoneTop, Now.close
        except:
            return None


    def HTFfindTradingZone(self, direction):
        return self.scanCircle(direction)


    def HTFfindOpposingZone(self, direction):
        if direction == 'Long': direction = 'Short'
        elif direction == 'Short': direction  = 'Long'

        return self.scanCircle(direction)

    #def LTFfindTradingZone(self, direction):
    #    print(self.scanCircle)


    def findAT(self, direction):
        Highest = self.highNow
        Lowest = self.lowNow
        found = False
        ATH = None
        ATL = None

        if direction == 'Long':

            for i in range(0, len(self.clist)-1):
                
                if self.clist[i].high > Highest:
                    ATH = self.clist[i].high
                    found = True
                    break

            if found == False:
                ATH = Highest

            return ATH

        elif direction == 'Short':

            for i in range(0, len(self.clist)-1):

                if self.clist[i].high < Lowest:
                    ATL = self.clist[i].low
                    found = True
                    break

            if found == False:
                ATL = Lowest

            return ATL





def convert(x):
# When GUI parameters enter Engine() they are all string.
# This method converts each case to either integer or float 
    try:
        return int(x)
    except:
        try:
            return float(x)
        except:
            return x


#def g_df            (
#    table                                   ,
#    date    = datetime.utcnow().isoformat() ,
#    limit   = 100                           ,
#    ticker  = 'AAPL'                        ):
#    engine  = sltm.SQLAlchemyEBuilder(**sltm.g_config()['production_db_remote'])
#    if      limit == None   :
#        sql = '''
#        SELECT * FROM {table} WHERE 
#        (DATE({table}.date) <= '{date}' AND ticker = '{ticker}') 
#        ORDER BY {table}.date DESC;'''.format(
#        table   = table ,
#        date    = date  ,
#        ticker  = ticker)
#    else                    :
#        sql = '''
#            SELECT * FROM {table} WHERE 
#            (DATE({table}.date) <= '{date}' AND ticker = '{ticker}') 
#            ORDER BY {table}.date DESC LIMIT {limit};'''.format(
#            table   = table ,
#            date    = date  ,
#            limit   = limit ,
#            ticker  = ticker)
#    
#    df = pd.read_sql(sql, engine.engine).iloc[::-1].set_index('date')
#    print(df)
#    return df[['open', 'high', 'low', 'close']]


#def g_partial_dfs   (
#    df          ,
#    start_date  ,
#    limit       ,
#    end_date    ):
#    df  = df.reset_index()
#    if start_date   :
#        df  = df[(df['date']>= start_date)]
#    if end_date     :
#        df  = df[(df['date']<= end_date)]
#    print(len(df), limit)
#    for i in range(len(df)- limit):
#        yield df[i:i+limit].set_index('date')

class Engine():
    
    def __init__(self, **kwargs):

        logging.basicConfig(level=0, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.getLogger('Application Logger').setLevel(logging.INFO)

        # Receives input parameters from GUI 
        # kwargs['ticker'] would be 'APPL' for example
        #for k in kwargs :
        #    setattr(self, k, convert(kwargs[k]))
        #
        # All that following can be replaced by the 2 rows above
        # Just using for better vision
        self.ticker           = kwargs['ticker']
        self.asset            = kwargs['asset']
        self.time_frame       = kwargs['time_frame']
        self.direction        = kwargs['direction']
        self.s_date           = kwargs['s_date']
        self.e_date           = kwargs['e_date']
        self.htf_params       = {'range': kwargs['htf_range'], 'liX': kwargs['htf_legin_value'], 'loX': kwargs['htf_legout_value'], \
                                 'liSZr': kwargs['htf_SZlegin_ratio'], 'loSZr': kwargs['htf_SZlegout_ratio'], 'bSZr': kwargs['htf_SZbase_ratio'], \
                                 'liDZr': kwargs['htf_DZlegin_ratio'], 'loDZr': kwargs['htf_DZlegout_ratio'], 'bDZr': kwargs['htf_DZbase_ratio']}
        self.ltf_params       = {'range': kwargs['ltf_range'], 'liX': kwargs['ltf_legin_value'], 'loX': kwargs['ltf_legout_value'], \
                                 'liDZr': kwargs['ltf_DZlegin_ratio'], 'loDZr': kwargs['ltf_DZlegout_ratio'], 'bDZr': kwargs['ltf_DZbase_ratio'], \
                                 'liSZr': kwargs['ltf_SZlegin_ratio'], 'loSZr': kwargs['ltf_SZlegout_ratio'], 'bSZr': kwargs['ltf_SZbase_ratio']} 
        self.frequency        = kwargs['frequency']
        self.execution_time   = kwargs['execution_time']
        self.legout_lh        = kwargs['legout_lh']
        
        # Debug
        #for k in kwargs:
            #print(k)
            #print(kwargs[k])
        # Debug


    def run (self):
        results = {}
        clist = []
        if self.ticker != '': # If we have supplied a ticket use it
            pairs = [self.ticker]    
        else                : # Or do for all tickers in config.json
            pairs = sltm.g_config()['pairs']
        if self.s_date == '':
            self.s_date = datetime.utcnow()
        
        try:
            for pair in pairs: # for each ticker in list pairs
                logging.info({'Parsing DataFrame': pair})

                # Get Data from CSV or DB
                try:
                    df = parseCSV(str(self.ticker) + '.csv')
                except FileNotFoundError as e:
                    logging.info('Could not load data.')
                    logging.info('File {} was not found in current directory, exiting..'.format(self.ticker + '.csv'))
                    exit()

                time.sleep(0.3)
                logging.info('\t+ DataFrame loaded')
                time.sleep(0.1)


                for row in df.iterrows():
                    cl  = Candle(row, self.htf_params)    # Import each row of DF as a new Candle item  
                    clist.append(cl)    # Add each new Candle to a list


                ##  HTF  SCAN  ##
                ##             ##
                HTF = Area(clist, self.htf_params, logging)
                logging.info('{} scan HTF..'.format(self.direction))
                TradingZone = HTF.HTFfindTradingZone(self.direction)
                
                if TradingZone:
                    logging.info("\t+ Found Trading Zone ")
                    if self.direction == 'Long':
                        logging.info("\t+ Demand Zone at  " + TradingZone[0] + ' - ' + TradingZone[1] + '\n')
                        DZTop = TradingZone[3]
                        Now = TradingZone[4]
                    elif self.direction == 'Short':
                        logging.info("\t+ Supply Zone at  " + TradingZone[0] + ' - ' + TradingZone[1] + '\n')
                        SZBot = TradingZone[2]
                        Now = TradingZone[4]
                else:
                    logging.info("\t+ No Trading Zone found..")

                OpposingZone = HTF.HTFfindOpposingZone(self.direction)
                
                if OpposingZone: # If we find Opposing Zone
                    logging.info("\t+ Found Opposing Zone ")
                    if self.direction == 'Long':
                        logging.info("\t+ Supply Zone at " + OpposingZone[0] + ' - ' + OpposingZone[1] + '\n')
                        SZBot = OpposingZone[2]
                        Now = TradingZone[4]
                    elif self.direction == 'Short':
                        logging.info("\t+ Demand Zone at " + OpposingZone[0] + ' - ' + OpposingZone[1] + '\n')
                        DZTop = OpposingZone[3]
                        Now = TradingZone[4]
                else: # If we dont find Opposing Zone look for ATH/ATL
                    logging.info(" No Opposing Zone found.")
                    logging.info("\t+ Now scanning for All-time High/Low..")
                    if self.direction == 'Long':
                        SZBot = None
                        ATH = HTF.findAT(self.direction) # SZBot
                        logging.info("\t+ Found all-time High " + str(ATH))

                    elif self.direction == 'Short':
                        DZTop = None
                        ATL = HTF.findAT(self.direction) # DZTop
                        logging.info("\t+ Found all-time Low " + str(ATL))
                ##              ##
                ##   ## ## ##   ##


                ##  HTF SCORING  ##
                ##               ##
                if self.direction == 'Long':
                    if SZBot and DZTop: # If we have proper Oppossing Zone
                        ATH = None
                        curve = {}
                        for i in range(1,6):
                            curve[i] = (i*(SZBot - DZTop)/5) + DZTop

                        for i in range(1,6):
                            if Now < curve[i]:
                                if i == 1:
                                    logging.info("Current price is Very Low on the curve.  Score = 2")
                                    score = 2
                                elif i == 2:
                                    logging.info("Current price is Low on the curve. Score = 1")
                                    score = 1
                    elif DZTop and ATH: # If Opposing Zone is ATH/ATL
                        score = 0

                    logging.info("\n   Price     {}\n   SZBot     {}\n   DZTop     {}\n   Score     {}\n   AT Hi     {}".format(Now, SZBot, DZTop, score, ATH))

                elif self.direction == 'Short':
                    if SZBot and DZTop: # If we have proper Oppossing Zone
                        ATL = None
                        curve = {}
                        for i in range(1,6):
                            curve[i] = (i*(SZBot - DZTop)/5) + DZTop

                        for i in range(1,6):
                            if Now < curve[i]:
                                if i == 5:
                                    logging.info("Current price is Very High on the curve.  Score = 2")
                                    score = 2
                                elif i == 4:
                                    logging.info("Current price is High on the curve. Score = 1")
                                    score = 1

                    elif SZBot and ATL: # If Opposing Zone is ATH/ATL
                        score = 0

                    logging.info("\n   Price     {}\n   SZBot     {}\n   DZTop     {}\n   Score     {}\n   AT Lo     {}".format(Now, SZBot, DZTop, score, ATL))

                ##              ##
                ##   ## ## ##   ##


                

                # Dereference all Candles and Ranges with __del__
                # Go To ITF..
        except KeyboardInterrupt:
            raise(KeyboardInterrupt)
        except Exception as e:
            print(e)
            traceback.print_exc()
            pass
        
        return results


def htf():
    pass

def itf(
    df                  ,
    time_frame= 'Weekly',
    position  = 'Long'  ):

    df = df.copy()
    if time_frame == 'Weekly':
        df['sma']   = df['close'].rolling(20).mean()
        df['ema']   = df['close'].ewm(5).mean()

    score       = df['ema'][-1] > df['sma'] [-1]
    score       = not score if position=='Short' else score 

    return df, 1 if score else 0

def ltf():
    pass



