import sys
import json
import requests
import urllib3
urllib3.disable_warnings()
import os, time, datetime


class Requests(object):
    def get_requests(self):
        if self.httpv2:
            s = requests.Session()
            s.mount(self.baseurl, HTTP20Adapter())
            s.verify = False
            return s
        else:
            return requests

    def get(self, url, params=None, headers=None, stream=False):
        return self.get_requests().get('%s%s' % (self.baseurl, url), params=params, headers=headers, verify=False,
                                       stream=stream)

    def getInfoFromURL(self, url, params=None, headers=None):
        return self.get_requests().get('%s' % url, params=params, headers=headers, verify=False)

    def put(self, url, data, headers=None):
        return self.get_requests().put('%s%s' % (self.baseurl, url), data=(None if data is None else json.dumps(data)),
                                       headers=headers, verify=False)

    def putText(self, url, data, headers=None):
        return self.get_requests().put('%s%s' % (self.baseurl, url), data=data, headers=headers, verify=False)

    def post(self, url, data=None, headers=None):
        return self.get_requests().post('%s%s' % (self.baseurl, url), data=(None if data is None else json.dumps(data)),
                                        headers=headers, verify=False)

    def patch(self, url, data, headers=None):
        return self.get_requests().patch('%s%s' % (self.baseurl, url),
                                         data=(None if data is None else json.dumps(data)), headers=headers,
                                         verify=False)

    def delete(self, url, headers=None):
        return self.get_requests().delete('%s%s' % (self.baseurl, url), headers=headers, verify=False)

    def post_archive(self, url, data=None, headers=None):
        headers["Content-Type"] = "application/zip"
        return self.get_requests().post('%s%s' % (self.baseurl, url), data=(None if data is None else data),
                                        headers=headers, verify=False)



class Middleware(Requests):
    def __init__(self, ip, username="demo", password="demo", logger=None, enablehttp2=False):
        self.logger = logger
        self.httpv2 = enablehttp2
        if username != None:
            self.username = username
        if password != None:
            self.password = password
        if ip != None:
            self.ip = ip
 
        self.url_top = 'https://%s/api/v2' % self.ip
        self.baseurl = 'https://%s' % self.ip
        self.auth_token = self.getToken()
        self.headers = {'authorization': self.auth_token}
        #self.configFname = "F:\ixia\tkamei\Automation\b2b.zip"

	
    def getToken(self):
        print('Getting the auth_token...')
        try:
            apiPath = '/auth/realms/keysight/protocol/openid-connect/token'
            self.headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            payload = { "grant_type" : "password", "username" : self.username, "password": self.password, "client_id": "clt-wap" }
            # use requests.post because payload is not json format as it is used in self.post()
            response = requests.post(self.baseurl + apiPath, data=payload, headers=self.headers, verify=False)
            #print('auth_token: {}'.format(response.json()['access_token']))
        except Exception as e:
            print(e)
            return ""

        return response.json()["access_token"]

    def importConfig(self):
        print('importing the config...')
        try:
            print("TRY")
#            self.headers = {'Accept: application/json', 'Authorization: %s', self.auth_token,'Content-Type: application/zip'}
            #self.headers = {"Accept: application/json, text/plain, */*","Accept-encoding: gzip, deflate, br", 'Authorization': self.auth_token, "Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryOVYQz30JsuRiZq1V"}
            apiPath = '/configs/operations/import'
            response = requests.post(self.baseurl + apiPath, data='@F:\ixia\tkamei\Automation\b2b\restSample.zip', headers=self.headers, verify=False)
        except Exception as e:
            print("ERROR")
            print(e)
            return ""

        return response()
        
    def getAllSessions(self):
        response = self.get('/api/v2/sessions', headers=self.headers)
        self.testcase.assertEquals(response.status_code, 200)
        sessions = []
        for item in response.json():
            sessions.append(item['id'])

        return sessions
        
    def getSessionInfo(self, sessionID, statusCode=200):
        response = self.get('/api/v2/sessions/{0}'.format(sessionID), headers=self.headers)
        #self.testcase.assertEquals(response.status_code, statusCode)
        return response.json()['configUrl']

    def newSession(self, configName=None, configID=None, configJson=None, configArchive=None, statusCode=201, sessionType='fullCore'):
        """
        :param configName:
        :param configID: specify a configID to create a new config and load the config with configID
        :param config: config in json format that will be uploaded and attached to the new session
        :return: new session ID
        """

        if sessionType == "fullCore":
            configType = "wireless-fullcore-config"

        if (configName == None and configJson == None and configID == None and configArchive == None):
            config = {"ConfigUrl": configType}
        elif configID != None:
            config = {"ConfigUrl": configID}
        elif (configName != None):
            # in this case create a new config by loading a specified config name
            config = self.selectConfig(configName)
            uploadedConfig = self.uploadConfig(config=config)
            config = {"ConfigUrl": 'configs/' + uploadedConfig[0]['id']}
        elif (configJson != None):
            uploadedConfig = self.uploadConfig(config=configJson)
            config = {"ConfigUrl": 'configs/' + uploadedConfig[0]['id']}
        elif configArchive != None:
            uploadedConfig = self.uploadConfig(configArchive=configArchive)
            config = {"ConfigUrl": 'configs/' + uploadedConfig[0]['id']}
        else:
            self.logger.error("NewSession: Unhandled case")

        response = self.post('/api/v2/sessions', config, headers=self.headers)

        #print(response.status_code)
        statusCode = response.status_code
        #self.testcase.assertEquals(response.status_code, statusCode)
        if statusCode == 201:
            # self.logger.debug(pformat(response.json()))
            return response.json()[0]['id']
        else:
            return response.json()

    def startTest(self, sessionID, result='SUCCESS', wait=40, statusCode=202):
        response = self.post('/api/v2/sessions/{0}/test-run/operations/start'.format(sessionID), headers=self.headers)
        #self.logger.debug(pformat(response.content))
        #self.logger.debug(pformat(response.json()))

#        self.testcase.assertEquals(response.status_code, statusCode)
        waitTime = wait

        rest_url = '/api/v2/sessions/{0}/test-run/operations/start/{1}'.format(sessionID, response.json()['id'])

        while wait > 0:      
            try:
                state = self.get(rest_url, headers=self.headers)
                # self.logger.debug(pformat(state))
                # self.logger.debug(pformat(state.content))

                if state.json()['state'] == result:
                    return state.json()

                if state.json()['state'] == 'ERROR':  # break when start goes to ERROR state
                    break

                wait -= 1
                time.sleep(2)
                #self.logger.debug(pformat(state.json()))

            except:
                return response.json()

#        else:
 #           self.testcase.assertTrue(False, msg='Test failed to start in {} sec'.format(waitTime))
        
        # if state is ERROR, stop the test and print the error message.
  #      self.testcase.assertTrue(False, msg='State: {} - Error MSG: {}'.format(state.json()['state'], state.json()['message']))  

    def stopTest(self, sessionID, result='SUCCESS', wait=40, statusCode=202):
        response = self.post('/api/v2/sessions/{0}/test-run/operations/stop'.format(sessionID), headers=self.headers)
        # self.logger.debug(pformat(response.content))
        # self.logger.debug(pformat(response.status_code))

#        self.testcase.assertEquals(response.status_code, statusCode)

        rest_url = '/api/v2/sessions/{0}/test-run/operations/stop/{1}'.format(sessionID, response.json()['id'])

        while wait > 0:
            try:
                state = self.get(rest_url, headers=self.headers)
                # self.logger.debug(pformat(state))
                # self.logger.debug(pformat(state.content))

                if state.json()['state'] == result:
                    return state.json()

                if state.json()['state'] == 'ERROR':  # break when start goes to ERROR state
                    break

                wait -= 1
                time.sleep(2)
                #self.logger.debug(pformat(state.json()))

            except:
                return response.json()

 #       else:
 #           self.testcase.assertTrue(False, msg='Test failed to stop')

        # if state is ERROR, stop the test and print the error message.
  #      self.testcase.assertTrue(False, msg='State: {} - Error MSG: {}'.format(state.json()['state'], state.json()['message']))

    def deleteSession(self, sessionID, statusCode=204):
        response = self.delete('/api/v2/sessions/{0}'.format(sessionID), headers=self.headers)
        # print response
        #self.testcase.assertEquals(response.status_code, statusCode)
        if '200' in str(response.status_code):
            #self.testcase.assertTrue(True if sessionID not in self.getAllSessions() else False)
            return response
        elif '204' in str(response.status_code):
            #self.testcase.assertTrue(True if sessionID not in self.getAllSessions() else False)
            return response
        else:
            #self.logger.debug(pformat(response))
            return response.status_code

  
    def checkSessionState(self, sessionID, status, waitTime=300):
        elapsedTime = 0
        testResponse = self.get('/api/v2/sessions/{0}/test'.format(sessionID), headers=self.headers)  
        while elapsedTime < waitTime and testResponse.json()['status'] != status:
            try:
                testResponse = self.get('/api/v2/sessions/{0}/test'.format(sessionID), headers=self.headers)
            except ConnectionError as e:
                break
            time.sleep(5)
            elapsedTime += 5
        return True if testResponse.json()['status'] == status else False    

    def getSessionStatus(self, sessionID):
        response = self.get('/api/v2/sessions/{0}/test'.format(sessionID), headers=self.headers)
        #self.testcase.assertEquals(response.status_code, 200)
        return response.json()['status']

    def getTestID(self, sessionID):
        response = self.get('/api/v2/sessions/{0}/test'.format(sessionID), headers=self.headers)
        #self.testcase.assertEquals(response.status_code, 200)
        return response.json()['testId']
        
    def selectConfig(self, configName):
        configFileName = 'configs/{0}.json'.format(configName)
        assert os.path.isfile(configFileName)

        file = open(configFileName)
        config = file.read()
        file.close()

        configJson = json.loads(config)
        #self.logger.debug(pformat(configJson))
        return configJson


    def uploadConfig(self, config=None, configArchive=None, statusCode=201):
        """
        :param config: in json format
        :return:
        """
        if config != None:
            response = self.post('/api/v2/configs', data=config, headers=self.headers)
            # self.logger.debug(pformat(response.content))
            self.logger.debug(pformat(response.reason))
            self.testcase.assertEquals(response.status_code, statusCode)
            return response.json()
        if configArchive != None:
            #with open("configs/" + configArchive, 'rb') as f:
            with open(configArchive, 'rb') as f:
                response = self.post_archive('/api/v2/configs',data=f, headers=self.headers)
                # self.logger.debug(pformat(response.content))
                # self.logger.debug(pformat(response.reason))
                # self.testcase.assertEquals(response.status_code, statusCode)
                return response.json()
                
    def waitTest(testEngine, testDuration, testID):
        header = ['TestDuration', 'ElapsedTime', 'Registration Initiated', 'Succeeded', 'Failed']
        columnLen = len(max(header, key=len))
        headerFormat = ("{:>%s}|" % columnLen) * len(header)
        bline = ['-' * columnLen] * len(header)
        print(headerFormat.format(*bline))
        elapsedTime = 0
        while elapsedTime < testDuration:
            #stats = testEngine.get('/api/v1/statistics')
            stats = getStatFullCoreREG(tetID)
            regInit = getStatValues(stats,'Registration Initiated')
            sessionsActive = getStatValuesSameTime(stats, 'n4-smf-pfcp-session-states', 'Active Sessions')
            sessionEstablishmentReqRate = getStatValuesSameTime(stats, 'n4-smf-session-messages-rate', 'PFCP Session Establishment Request Tx/s')
            sessionModificationReqRate = getStatValuesSameTime(stats, 'n4-smf-session-messages-rate', 'PFCP Session Modification Request Tx/s')
            sessionDeletionReqRate = getStatValuesSameTime(stats, 'n4-smf-session-messages-rate', 'PFCP Session Deletion Request Tx/s')
            sessionReportRxRate = getStatValuesSameTime(stats, 'n4-smf-session-messages-rate', 'PFCP Session Report Request Rx/s')
            rxPPS = getStatValuesSameTime(stats, 'n3-ran-data-packets-rate', 'GTPu Packets Rx/s')
            txPPS = getStatValuesSameTime(stats, 'n3-ran-data-packets-rate', 'GTPu Packets Tx/s')
        
            output = [testDuration, elapsedTime, sessionsActive, sessionEstablishmentReqRate, sessionModificationReqRate,sessionDeletionReqRate, sessionReportRxRate, rxPPS, txPPS]
            print(headerFormat.format(*header))
            print(headerFormat.format(*output))
            print(headerFormat.format(*bline))
            time.sleep(2)
            elapsedTime += 2
        print('\n')
        return False
        
    def getStatFullCoreREG(self, testID):
        response = self.get('/api/v2/results/{0}/stats/Fullcorengran_RegistrationProcedure'.format(testID), headers=self.headers)
        #self.testcase.assertEquals(response.status_code, 200)
        return response.json()

        
    def getStatAll(self, testID):
        response = self.get('/api/v2/results/{0}/stats'.format(testID), headers=self.headers)
        #self.testcase.assertEquals(response.status_code, 200)
        return response.json()
    
    def getTimestamp(self, response):
        result = response['name']
        result = response['columns']['snapshots']
        return result
    
    def getStatValues(response, publisher, statName):
        result = 'na'
        for key in response.json():
            if key['publisher'] == publisher:
                for publisher in key['stats']:
                    if publisher['name'] == statName:
                        result = publisher['value']
        return result
                




if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("please specify configFileName in argument")
        print("e.g. %s configFileName.zip" % __file__)
        sys.exit(1)

    fileName = sys.argv[1]

    print("---- P3 getToken ----")
    mw = Middleware(ip='10.39.18.102')
    #mw = (ip='10.39.18.103', username='LC_Demo',password='admin')
    print("---- P5 importConfig ----")
    print("---- P7 createNewSession ----")
    #fileName = "restSample.zip" # config name found in configs folder
    newSessionID = mw.newSession(configArchive=fileName)  # start session using the specified config
    
    print("---- P8 startTest ----")
    mw.startTest(newSessionID)
    startTime = datetime.datetime.now()     # take current time. Will be used inside HTML report    
    print(startTime)
    state = mw.checkSessionState(newSessionID, status='STARTED')
    #self.assertEqual(state, True, "The test did not start")  # check if test started
    print(mw.getSessionStatus(newSessionID))

    time.sleep(30)    
#    if sys.version_info.major == 2:
#        strKeys = raw_input('Enter return to List Statistics')
#    elif sys.version_info.major == 3:
#        strKeys = input('Enter return to List Statistics')
    print("---- P10 getTestID ----")
    testID = (mw.getTestID(newSessionID))
    print('testID: %s' % testID)
    
    print("---- P11 listStatistics ----")
    res=mw.getStatAll(testID)
    for i in res:
        if i['name'].find('Fullcorengran') != -1:
            print(i['name'])

#    if sys.version_info.major == 2:
#        strKeys = raw_input('Enter return to Get Statistics (Fullcorengran_RegistrationProcedure)')
#    elif sys.version_info.major == 3:
#        strKeys = input('Enter return to Get Statistics (Fullcorengran_RegistrationProcedure)')    
    print("---- P12 getStatistics ----")
    res=mw.getStatFullCoreREG(testID)
    print(res['name'])
    print(res['columns'])
    for i in res['snapshots']:
        print(i['values'])

#   if sys.version_info.major == 2:
#        strKeys = raw_input('Enter return to Stop Test')
#    elif sys.version_info.major == 3:
#        strKeys = input('Enter return to Stop Test')
    time.sleep(10)
    print("---- P13 stopTest ----") 
    endTime = datetime.datetime.now()   # take time after test ends. Will be used inside HTML report
    print(endTime)
    mw.stopTest(newSessionID)
    print(mw.getSessionStatus(newSessionID))
    
#    if sys.version_info.major == 2:
#        strKeys = raw_input('Enter return to Delete Session')
#    elif sys.version_info.major == 3:
#        strKeys = input('Enter return to Delete Session')
    print("---- P17 deleteSession ----")
    mw.deleteSession(newSessionID)

