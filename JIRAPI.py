#import re
#from collections import Counter
import urllib3
#import ssl
#import getpass
import subprocess
import json
from sys import version_info
import re

#necessary python scripts
from myconfig import myCredentials

try:
   from jira import JIRA
except ImportError:
   if version_info >= (3, 0):
      #subprocess.call( ["sudo", "-H", "pip3", "install", "jira",  "requests",  "requests-oauthlib",  "ipython",  "filemagic",  "pycrypto"] )
      print("import Error with JIRA")
   else:
      #subprocess.call( ["sudo", "-H", "pip", "install", "jira",  "requests",  "requests-oauthlib",  "ipython",  "filemagic",  "pycrypto"] )
      print("import Error with JIRA")

class JIRAPI():
   gitlab_url = 'https://git.server.url'
   srv = ''
   regexRelId = re.compile(r"\d+", re.DOTALL)
   regexPlatform = re.compile(r"u'(\w*)'", re.DOTALL)
   #
   #
   #
   def __init__(self,  project_name="DEFECT", credentials=None):
      self.__project_name = project_name

      if (credentials is None):
         self.credentials = myCredentials()
      else:
         self.credentials = credentials
      self.cred = self.credentials.getCredentials('dre')

      self.connect()
      self.mappingRelease = self.readReleaseMapping()

   def connection_info(self):
      if self.srv:
         return self.srv.client_info()

   def handleAuthError(self):
      print("Invalid Password")
      self.cred = self.credentials.getCredentials('dre', newPass=True)

   #
   #  until now no crt is supported only HTTP possible, insecure ... do not use with internet, secure solution possible see: JIRA-get-Tickets.py
   #
   #@classmethod
   def connect(self,  jira_server_url='https://jira.server.url'):
      self.__jira_options = {
         'server': jira_server_url,
         'verify': False
      }
      urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
      passCount = 0
      while (True):
         try:
            self.srv = JIRA(self.__jira_options, basic_auth=(self.cred['user'], self.cred['pass']))
            break
         except Exception as e:
            if (e.status_code == 401) or (e.status_code == 403):
               if (passCount >= 1):
                  print "ERROR Invalid Password\n%s" %(e.message)
                  break
               self.handleAuthError()
            else:
               print(e)
               break

      return self.srv

   #
   # get information from Relevant to Platform alias customfield_15300
   #
   def getRelevantToPlatform(self, issue_object):
      platform = []
      if self.srv :
         if issue_object:
            defect = issue_object.key
            if ('DEFECT' in defect) or ('BUG' in defect) or ('FEATURE' in defect):
               tmp = "{}".format( issue_object.fields.customfield_15300 )
               for line in re.findall(self.regexPlatform, tmp):
                  platform.append(line)
      return platform

   #
   # get SOP Date customfield
   #
   def getSOPDate(self, issue_object):
      sopdate = ""
      if issue_object:
         if ('FEATURE' not in issue_object.key) and ('REQ' not in issue_object.key):
            if ('DEFECT' in issue_object.key):
               sopdate = issue_object.fields.customfield_10316 # get the ID of Value behind
               URL = "https://jira.server.url" + issue_object.key + "/customfield_10316"
               data = self.manualcall(URL)
               data = data.decode()
               sopdate = json.loads(data)
               sopdate = sopdate['displays'][0]

            elif ('FEATURE' in issue_object.key):
               sopdate = issue_object.fields.customfield_13701
            else:
               print("Ticket Type not supported. Only FEATURE or DEFECT")
      return sopdate
   #
   def readReleaseMapping(self):
      mapping = {}
      regexMap = re.compile(r"'|\s+")
      with open('SW-Versionen+IDs.txt', 'r') as infile:
         for line in infile:
            line = re.sub(regexMap, '', line).split(',')
            key = line[0]
            value = line[1]
            mapping[key] = value
      return mapping

   #
   # return a List of JIRA Issues, querryd from JIRA JQL Filter, no JQL valid check
   #
   def getDEFECTS(self,  jira_filter='project=DEFECT and status = Processed'):
      issues_in_project = None
      if self.srv :
         issues_in_project = self.srv.search_issues(jira_filter, maxResults=500)
      return issues_in_project

   #
   # return a String List of DEFECTS from a giving JIRA Filter
   #
   def getDEFECTSFromFilter(self, jira_filter='project=DEFECT and status = Processed'):
      jira_objects = self.getDEFECTS(jira_filter)
      list_of_defects = []
      output_string = ""
      for obj in jira_objects:
         output_string += obj.key + '\n'
         list_of_defects.append( obj.key )

      with open('ListOfDefectsFromFilter.txt', 'w') as the_file:  # 'a' for appending
         the_file.write( output_string )

      return list_of_defects

   #
   # return a JIRA DEFECT
   #
   def getJIssue(self, defect=''):
      issue_object = None
      if (isinstance(defect, str)) and (defect != '') and (self.srv):
         try:
            issue_object = self.srv.issue(defect)
         except Exception as e:
            print (e.text)
      return issue_object

   #
   # return a JIRA DEFECT
   #
   def getResolution(self, issue='DEFECT-8435'):
      issue = None
      resolution = None
      if self.srv :
         issue = self.srv.issue(issue, fields='resolution,status')
         resolution = issue.fields.resolution
      return "{}".format(resolution)

   #
   # return a JIRA DEFECT, returns Tuple (Status, QSapproval)
   #
   def getDEFECTstatusAndQS(self, issue='DEFECT-8000'):
      s1 = ""
      s2 = ""
      if self.srv :
         issue_object = self.srv.issue(issue)
         if issue_object:
            ticket_status = issue_object.fields.status
            s1 = "{}".format(ticket_status)
            if ('FEATURE' in issue):
               s2 = ""
            elif ('REQ' in issue):
               s2 = ""
            else:
               qsapproval = issue_object.fields.customfield_10126
               #ticket_status = issue_object.fields.status
               #print("QS: ", qsapproval,  " status: ",  ticket_status)
               #s1 = "{}".format(ticket_status)
               s2 = "{}".format(qsapproval)

      return ( s1 , s2 )

   #
   #  get QS approval : Approval of QA-SW
   #
   def getStatus(self, issue_object):
      status = issue_object.fields.status
      return "{}".format(status)

   #
   #  get QS approval : Approval of QA-SW
   #
   def getQSapproval(self, issue_object):
      ret = ''
      defect = issue_object.key
      if ('FEATURE' not in defect) and ('REQ' not in defect):
         qsapproval = issue_object.fields.customfield_10126
         ret = "{}".format(qsapproval)
      return ret

   #
   # get Verifiable in SW Field, no access without admin permission to that values in jira
   #
   def getVerifiableInSW(self,  issue_object):
      verifyInSW = None
      if self.srv :
         if issue_object:
            defect = issue_object.key
            if ('FEATURE' not in defect) and ('REQ' not in defect):
               verifyInSW = issue_object.fields.customfield_14002
      return "{}".format(verifyInSW)

   #
   # get the Approval for integration in SW Field, ID Fields Values are stored in pentaho system
   #
   def getApprovalForIntegrationSW(self, issue_object):
      approval = []
      if self.srv :
         if issue_object:
            defect = issue_object.key
            if ('DEFECT' in defect) or ('BUG' in defect) or ('FEATURE' in defect):
               list = "{}".format( issue_object.fields.customfield_10400 )
            else:
               list = 'None'
            if (list != 'None'):
               tmpIds = re.findall(self.regexRelId, list)
               for id in tmpIds:
                  if (id in self.mappingRelease):
                     rel = self.mappingRelease[id]
                  else:
                     rel = '[%s]' %(id)
                  approval.append(rel)
                  pass

      return approval

   #
   # get duedate Field
   #
   def getDueDate(self, issue_object):
      duedate = None
      if self.srv :
         if issue_object:
            defect = issue_object.key
            if ('FEATURE' not in defect) and ('REQ' not in defect):
               duedate = issue_object.fields.duedate
      return "{}".format(duedate)

   #
   # get updated Field
   #
   def getupdatedDate(self, issue='DEFECT-8435'):
      updated = None
      if self.srv :
         issue_object = self.srv.issue(issue)
         if issue_object:
            updated = issue_object.fields.updated
      return "{}".format(updated)

   #
   # get summary Field, ist die Ueberschrift des Tickets
   #
   def getSummary(self, issue='DEFECT-8435'):
      summary = None
      if self.srv :
         issue_object = self.srv.issue(issue)
         if issue_object:
            summary = issue_object.fields.summary
      return "{}".format(summary)

   #
   # get description Field, ist die Beschreibung des Tickets
   #
   def getDescription(self, issue='DEFECT-8435'):
      description = None
      if self.srv :
         issue_object = self.srv.issue(issue)
         if issue_object:
            description = issue_object.fields.description
      return "{}".format(description)

   #
   # get priorty Field, ist die Prioritaet des Tickets
   #
   def getPrioritaet(self, issue='DEFECT-8435'):
      prio = None
      if self.srv :
         issue_object = self.srv.issue(issue)
         if issue_object:
            prio = issue_object.fields.priority.name
      return "{}".format(prio)

   #
   # get Label Field from JIRA Tickets
   #
   def getLabel(self, issue_object):
      label = []
      defect = issue_object.key
      if ('FEATURE' not in defect) and ('REQ' not in defect):
         label = issue_object.fields.labels
      return label

   #
   # get IntegratedIntoSW Field from JIRA Tickets
   #
   def getSuggestedForIntegrationInSW(self, issue_object):
      suggestedSW = []
      defect = issue_object.key
      if ('FEATURE' in defect) and ('REQ' not in defect) and ('DEFECT' not in defect):
         suggestedForIntegrationInSW = issue_object.fields.customfield_14402
         suggestedSW = "{}".format(suggestedForIntegrationInSW)
      return suggestedSW

   #
   # get Team-develop Field
   #
   def getTeamDevelopment(self,  issue='DEFECT-8435'):
      issue = None
      teamdevel = None
      if self.srv :
         if issue:
            teamdevel = issue.fields.customfield_10305
            teamdevel = self.TeamDevelopMapping(teamdevel)
      return teamdevel

   #
   # misc mapping Method from literal in customfield to String, no access without admin permission to that values in jira
   #
   def TeamDevelopMapping(self,  list_str):
      if list_str[0] == '35':
         return 'System-System'
      elif list_str[0] == '36':
         return 'System-Basisfunktion'
      elif list_str[0] == '37':
         return 'System-Vernetzung'
      else:
         return ''

   #
   # get all Git Information from a JIRA DEFECT
   # thanks to Martin Doedtmann and Kai Ehrhart from AMB
   def getGitInformationFromComments(self, issue='DEFECT-8000'):
      if self.srv:
         issue = self.srv.issue(issue, fields='comment')
         #print(issue.fields.status)
         for comment in issue.fields.comment.comments:
            if comment.updateAuthor.displayName == "gitlab" or comment.updateAuthor.displayName == "svc_jira-gitlab":
               git_info = comment.body[(comment.body.find("a commit of ") + len("a commit of ")):]

      return git_info

   #
   # get a List of Modules from JIRA DEFECT where gitlab changes (which Modules participate on that DEFECT)
   # thanks to Martin Doedtmann and Kai Ehrhart from AMB
   def getModules(self, issue_with_key):
      liste = []
      if self.srv:
         issue = self.srv.issue(issue_with_key, fields='comment')
         #print(issue.fields.status)

         for comment in issue.fields.comment.comments:
            if comment.updateAuthor.displayName == "gitlab" or comment.updateAuthor.displayName == "svc_jira-gitlab":
               git_info = comment.body[(comment.body.find("a commit of ") + len("a commit of ")):]
               module = git_info[(git_info.find("/") + 1):git_info.rfind("|")]
               liste.append(module)

      # unique the list
      liste = list(set(liste))
      return liste

   #
   # get a List of Commit ID from JIRA ISSUE / DEFECT
   # thanks to Martin Doedtmann and Kai Ehrhart from AMB
   def getCommitIDs(self, issue_with_key):
      liste = []
      if self.srv:
         issue = self.srv.issue(issue_with_key, fields='comment')
         #print(issue.fields.status)
         for comment in issue.fields.comment.comments:
            if comment.updateAuthor.displayName == "gitlab" or comment.updateAuthor.displayName == "svc_jira-gitlab":
               git_info = comment.body[(comment.body.find("a commit of ") + len("a commit of ")):]
               commit_url = git_info[git_info.index(self.gitlab_url):git_info.index("]")]
               commit_id = commit_url[(commit_url.rfind("/") + 1):]
               liste.append(commit_id)
      # unique the list
      liste = list(set(liste))
      return liste

   #
   # get a List of Modules with CommitIDs from JIRA DEFECT where gitlab changes (which Modules participate on that DEFECT)
   #
   def getModulesWithCommitIDs(self, issue_with_key):
      liste = []
      pair_module_commit = ()
      if self.srv:
         issue = self.srv.issue(issue_with_key, fields='comment')

         for comment in issue.fields.comment.comments:
            if comment.updateAuthor.displayName == "gitlab" or comment.updateAuthor.displayName == "svc_jira-gitlab":
               git_info = comment.body[(comment.body.find("a commit of ") + len("a commit of ")):]
               module = git_info[(git_info.find("/") + 1):git_info.rfind("|")]
               commit_url = git_info[git_info.index(self.gitlab_url):git_info.index("]")]
               commit_id = commit_url[(commit_url.rfind("/") + 1):]
               pair_module_commit = ( module, commit_id )
               liste.append( pair_module_commit )

      # unique the list
      liste = list(set(liste))
      return liste

   #
   # set a ISSUE / DEFECT customfield_14002 = "Verifiable in SW" to a value (is hashed, no acces to JIRA DB possible ... plugin Problem)
   #     dirty solution get hash onetime from a ticket
   #     search for customfield_14002 value and give it this function, customfield_14002=["144601"] means: ...
   #
   def setTransistionForDefect(self, issue_with_key, value="144601"):
      if self.srv:
         self.srv.transition_issue(issue_with_key, '91', customfield_14002=[value])

   #
   # setStatus to integrated for a list of DEFECT, ['DEFECT-1234', 'DEFECT-1253', ...]
   # RC_VERSION_HASH TODO: do mapping or query function
   #
   def setStatus(self, listOfDEFECTS, RC_VERSION_HASH):
      for defect in listOfDEFECTS:
         self.srv.setTransistionForDefect(defect, RC_VERSION_HASH)
         print(defect, " is set to Integrated")

   # update Verifiable in SW Field of an Issue
   #
   def updateVerifiableInSW(self, issue_object, newVersion={}):
      isTransistion = False
      transistion_id = 0
      if issue_object:
         if 'text' in newVersion and 'id' in newVersion:
            print("please use: newVersion={'id':'148201'} or newVersion={'text':'Release-123'} not both!")
         # wrong Ticket Status, do transistion issue
         status = str(issue_object.fields.status)
         if status == "Closed" or status == "Integration finished":
            #print("{} is {}".format(issue_object.key, issue_object.fields.status))
            #return
            #TODO: call transistion issue function
            transistions = self.srv.transitions(issue_object)
            for transition in transistions:
               if transition['name'] == "correct issue":
                  transition_id = transition['id']
                  break
            isTransistion = True
         # get old Verfiable in SW Data and convert newVersion Data to JIRA intern ID
         old_data = issue_object.fields.customfield_14002
         new_data = []
         fieldId = []
         try:
            if 'text' in newVersion:
               tmp = newVersion['text']
               for key, value in self.mappingRelease.items():
                  if tmp == value:
                     #print("match")
                     #print(key)
                     #print(value)
                     new_data = key
                     break
               else:
                  print("not found in mapping Table")
            elif 'id' in newVersion:
               new_data = newVersion['id']

            if type(new_data) is not list:
               new_data = [new_data]
            def to_string(x):
               return str(x)
            if type(new_data) is list:
               map(to_string, new_data)
         except ValueError as e:
            print(e)
         # update the jira_issue
         if self.srv:
            #print("old: ",old_data)
            #print("new: ",new_data)
            for element in new_data:
               if element not in old_data:
                  fieldId = old_data + new_data
                  try:
                     if isTransistion == False:
                        issue_object.update( fields={"customfield_14002": fieldId} )
                     elif isTransistion == True:
                        self.srv.transition_issue( issue_object, transition_id, fields={"customfield_14002": fieldId} )
                     print("{} is set now for {}".format(new_data, issue_object.key))
                  except Exception as e:
                     print("Konnte die Version nicht in das Ticket {} schreiben. Ursache: {}".format(issue_object.key,e))
               else:
                  pass
                  #print("{} is in {} already set".format(element, issue_object.key))

   #
   #  check Ticket for QSStatus
   #
   def checkTicket(self,  defect="DEFECT-11192"):
      if isinstance(defect, str):
         ret = self.getDEFECTstatusAndQS(defect)
         return ret
      else:
         # this is not a string maybe jira object
         raise Exception

   #
   #  get getMergeRequests
   #
   def getMergeRequests(self, issue_object):
      links = []
      defect = issue_object.key
      if self.srv:
         link_objects = self.srv.remote_links( issue_object.key )
         for link in link_objects:
            if hasattr(link, "object"):
               if hasattr(link.object, "url"):
                  if ("merge_requests" in link.object.url):
                     links.append( link.object.url )
      return links

   #
   #  get Deteils for Jira Item
   #
   def getJiraItemDetails2(self, issue='DEFECT-15531'):
      item = {'status':'', 'QS':'', 'label':[], 'integrateInSW':'', 'duedate':''}
      if isinstance(issue, str):
         if self.srv :
            issue_object = self.srv.issue(issue)
            if issue_object:
               ticket_status = issue_object.fields.status
               item['status'] = "{}".format(ticket_status)

               if ('FEATURE' in issue):
                  suggestedForIntegrationInSW = issue_object.fields.customfield_14402
                  item['integrateInSW'] = "{}".format(suggestedForIntegrationInSW)
               elif ('REQ' in issue):
                  pass
               # DEFECT, BUG, ...
               else:
                  qsapproval = issue_object.fields.customfield_10126
                  suggestedForIntegrationInSW = issue_object.fields.customfield_10400
                  duedate = issue_object.fields.duedate
                  ticket_label = issue_object.fields.labels
                  item['QS'] = "{}".format(qsapproval)
                  item['integrateInSW'] = "{}".format(suggestedForIntegrationInSW)
                  item['duedate'] = "{}".format(duedate)
                  item['label'] = ticket_label

      return item

   #
   #  get Deteils for Jira Item
   #
   def getJiraItemDetails(self, defect):
      details = {'status':'', 'QS':'', 'label':[], 'duedate':'', 'MR':[], 'approval':[], 'relevantToPlatform':[], 'SOP Date':''}

      issue_object = self.getJIssue(defect)
      if (issue_object is not None):
         details['status'] = self.getStatus(issue_object)
         details['QS'] = self.getQSapproval(issue_object)
         details['label'] = self.getLabel(issue_object)
         details['duedate'] = self.getDueDate(issue_object)
         details['MR'] = self.getMergeRequests(issue_object)
         details['approval'] = self.getApprovalForIntegrationSW(issue_object)
         details['relevantToPlatform'] = self.getRelevantToPlatform(issue_object)
         details['SOP Date'] = self.getSOPDate(issue_object)

      return details

   #
   # set for a jira filter the VerifiableInSW
   #
   def setJIssues(self, jira_filter, newVerifiableInSW={'text':'Release-123'}):
      issue_objects = self.getDEFECTS(jira_filter=jira_filter)
      if issue_objects:
         if 'text' in newVerifiableInSW:
            for issue_object in issue_objects:
               self.updateVerifiableInSW( issue_object, newVersion=newVerifiableInSW )
         else:
            print("no valid Version for a Jira Issue set.")
      else:
         print("no valid jira objects received.")

   #
   # manually calling jira rest api
   #
   def manualcall(self, calldata):
      output = ""
      try:
         cmd = ['curl', '-u', self.cred['user']+':'+self.cred['pass'], '-k', '-X', 'GET', '-H', "Content-Type: application/json", calldata]
         p_gitlog = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
         output, err = p_gitlog.communicate()
         #print(output)
      except subprocess.CalledProcessError as err:
         print(err.output, err.returncode, err.message)
      except Exception as err:
         print err
      if (p_gitlog.returncode != 0):
         print err
      return output


if __name__ == "__main__":
   from myconfig import myConfig
   #from moduleconfig import moduleConfig
   config = myConfig()

   jira = JIRAPI(credentials=config.credentials)

   #itemDetails = jira.getJiraItemDetails('DEFECT-15531')
   #approval = jira.getApprovalForIntegrationSW( jira.getJIssue('DEFECT-15531') )

   #jira.updateVerifiableInSW( jira.getJIssue('ZZZDEF-81'), newVersion={'id':['148204','148205']} )
   #jira.updateVerifiableInSW( jira.getJIssue('ZZZDEF-81'), newVersion={'text':'Release-123'} )

   #fi = input("Bitte JIRA Filter eingeben: ")
   #jira.setJIssues(jira_filter=fi, newVerifiableInSW={'text':'Release-123'})
   #pass




   #data = jira.getGenericCustomfield(jira.getJIssue('DEFECT-1234'), customfield_name="Verifiable in SW")
   #print(data)

   data = jira.getSOPDate(jira.getJIssue('DEFECT-31016'))
   print(data)
