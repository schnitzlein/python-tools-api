import re
import tsdGitLab
import JIRAPI
import myconfig
import helper
import reviewBoard

regexJiraId = re.compile(r"(?:REQ|FEATURE|DEFECT|BUG)-\d+", re.DOTALL) # thanks to sven pietschman

def warn_print(text):
   print(helper.bcolors.WARNING + text + helper.bcolors.ENDC)

def jira_check(description):
   merge = False
   all_JIRA_TICKETS = ""
   if 'REV' in description or 'Reviewed at' in description:
      #print('Review OK')
      pass
   all_JIRA_TICKETS = re.findall(regexJiraId, description)
   if all_JIRA_TICKETS != []:
      for item in all_JIRA_TICKETS:
         tmp_data = jira_obj.getJiraItemDetails(item.encode())
         #print(tmp_data)
         if tmp_data['status'] == "Processed" or tmp_data['status'] == 'Approved':
            if tmp_data['QS'] == 'OK':
               #if tmp_data['approval']:
               merge = True # merge
               #else:
               #   warn_print("no approval")
               #   merge = False
            else:
               #warn_print("no QS OK for: {}".format(tmp_data['MR']))
               merge = False
         else:
            #warn_print("wrong Ticket Status for: {}".format(tmp_data['MR']))
            merge = False
   #print(all_JIRA_TICKETS)
   return merge

def get_reviewId(description):
   reviewId = re.search('.rev (\d+)', description, re.IGNORECASE)
   if (reviewId):
      reviewId = reviewId.group(1).encode("UTF-8")
   else:
      reviewId = re.search('/reviewboard/r/(\d+)', description, re.IGNORECASE)
      if (reviewId):
         reviewId = reviewId.group(1).encode("UTF-8") 
      else:
         reviewId = "None" 
   return reviewId        

gitlab_obj = tsdGitLab.GitlabAPI()
jira_obj = JIRAPI.JIRAPI()

gitlab_projects = []
mergerequest_list = []

preintegrators_list = ['svc_sys_vorint', '<username1>', '<username2>', '<username3>', '<username4>']

m = myconfig.myConfig()
m.getModuleConfig()
#modules = m.mconfig.getModuleList(['system', 'basis', 'carcom', 'test'], ['lib', 'api', 'comp'], 0, False)
modules = m.mconfig.getModuleList(['carcom'], ['lib', 'api', 'comp'], 0, False)
for i in modules:
   if i['recipe'] != '':
      module_name = i['url'].split('/')
      group_name = module_name[0].split(':')
      group_name = group_name[1]
      gitlab_project = group_name + '/' + module_name[1].replace(".git", "")
      #print(gitlab_project)
      gitlab_projects.append( gitlab_project )

# add <groupname>/<modulename>
gitlab_projects.append( '<groupname>/<modulename>' )
recipesMr = 0
for elems in gitlab_projects:
   if (elems != '<groupname>/<modulename>'):
      mergerequest = gitlab_obj.getMergeRequestInformation(elems)
      if mergerequest != []:
         mergerequest_list.append( mergerequest ) # pair of dictionary[0] obj[1]
   else:
      mergerequest = gitlab_obj.getMergeRequestInformation(elems)
      if mergerequest != []:
         for _ in range(len(mergerequest)):
            if (mergerequest[_]['assignee']):     
               if (mergerequest[_]['assignee']['username'].encode("UTF-8") in set(preintegrators_list)):
                   mergerequest_list.append( mergerequest[_] ) 
                   recipesMr += 1 

print("{} MergeRequests for <groupname>/<modulename> for System".format(recipesMr))
               
#get the members of gitlab group taskforce-codereview and imb group
lTaskforce = set(gitlab_obj.getGroupMembersByGroupID(1079))
lImb = set(gitlab_obj.getGroupMembersByGroupID(1378))

nonMergeable = []
mergeable = []
print("\nMR: STATUS src: SOURCE_BRANCH -> TARGET_BRANCH")
for mm in mergerequest_list:
   for m in mm:
      #======== get informations ======= #
      description = m['description']
      ready = jira_check(description)

      reviewId = get_reviewId(description)
      shipItCount = 0
      if (reviewId != "None"):
         reviewB = reviewBoard.reviewBoard(reviewId=reviewId)
         reviewInfo = reviewB.get_reviewBoard_info()
         shipItNames = set(reviewInfo['shipItNames'])
         shipItCount = reviewInfo['shipItCount']

      print("\nsrc: {} -> dest: {}".format(m['source_branch'], m['target_branch']))
      print(m['url'])

      # ======= Check for shipIts from reviewBoard ======= #
      shipIts = False
      # ship it is true when at least 3 shipIts, one from taskforce and one from imb(175er)
      if (shipItCount >= 3):
         if (shipItNames & lTaskforce):
            if (shipItNames & lImb):
               shipIts = True
      
      # ======= Jira, RevBoard and can_be_merged okay ====== #
      if (ready == True and reviewId != "None" and shipIts == True and m['merge_status'] == "can_be_merged"):
         print("nMR: {} src: {} -> {}".format(m['merge_status'], m['source_branch'], m['target_branch']))
         
         if (helper.query_yes_no("Do you want to merge MR: %s" %(m['url']),  'no') == 'yes'):
            gitlab_obj.mergeMergeRequest(m['url'])
            warn_print("MR is merged now. \n")
         else:
            warn_print("MR is not merged and added to the mergeable list \n")
            mr = {"mergeRequest": m, "JiraOkay": ready, "mergeable": m['merge_status'], "reviewId": True, "reviewInfo": reviewInfo}
            mergeable.append(mr)

      # ======= checks not okay ======= #
      else:
         if (reviewId != "None"):
            nonMr = {"mergeRequest": m, "JiraOkay": ready, "mergeable": m['merge_status'], "reviewId": True, "reviewInfo": reviewInfo}
            nonMergeable.append(nonMr)
            warn_print("MR can't be merged. \n")
         
         else:  
            #TODO check if rev id is in commits 
            nonMr = {"mergeRequest": m, "JiraOkay": ready, "mergeable": m['merge_status'], "reviewId": False, "reviewInfo": {}}
            nonMergeable.append(nonMr)
            warn_print("MR can't be merged because no proper REV ID is given. \n")

warn_print("{} merge requests can be merged, see mergeable[] for more Information".format(len(mergeable)))            
warn_print("{} merge requests can't be merged, see nonMergeable[] for more Information".format(len(nonMergeable)))
      
