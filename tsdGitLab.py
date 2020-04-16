#!/usr/bin/python
#import psycopg2
#import time
#import logging
import gitlab
import urllib3
import ssl

class GitlabAPI:

   # TODO: add SSL support
   def __init__(self, server_path='https://git.server.url', gitlab_token='<TOKEN-HERE-XXXXXXXXXXXXXXX>'):
      urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
      self.gl = None
      self.server_path = server_path
      try:
         self.gl = gitlab.Gitlab(server_path, gitlab_token, ssl_verify=False)
      except Exception:
         print("Exception occured on connection with server: {} token: {}".format(server_path, gitlab_token))

   def __del__(self):
      self.gl = None
      #print("Connection is now set to invalid.")


   def getMergeRequetDetails(self, mergerequest):
      tmp_dict = {}
      tmp_dict['project_id'] = mergerequest.project_id
      tmp_dict['mr_id'] = mergerequest.iid
      tmp_dict['status'] = mergerequest.attributes['state']
      user = mergerequest.attributes['author']
      tmp_dict['author'] = user['name']
      tmp_dict['source_branch'] = mergerequest.attributes['source_branch']
      tmp_dict['target_branch'] = mergerequest.attributes['target_branch']
      tmp_dict['source_branch_delete'] = mergerequest.attributes['should_remove_source_branch']
      tmp_dict['wip'] = mergerequest.attributes['work_in_progress']
      tmp_dict['merge_status'] = mergerequest.attributes['merge_status']
      tmp_dict['title'] = mergerequest.attributes['title']
      tmp_dict['description'] = mergerequest.attributes['description']
      tmp_dict['url'] = mergerequest.attributes['web_url']
      tmp_dict['assignee'] = mergerequest.attributes['assignee']
      return tmp_dict

   #
   #  returns a list of dictionary for open MergeRequests on this group/modulename
   #
   def getMergeRequestInformation(self, projectpath):
      open_mergerequests = []
      if self.gl:
         try:
            #projectpath = group+'/'+modulename
            project = self.gl.projects.get( projectpath )
            open_mr = project.mergerequests.list(all=True, state="opened")
            #all_mr = project.mergerequests.list(all=True)
            if len(open_mr) > 0:
               print('{} MergeRequests for {}'.format(len(open_mr), project.attributes['name']))
               for mergerequest in open_mr:
                  open_mergerequests.append( self.getMergeRequetDetails(mergerequest) )
         except Exception as e:
            print("unable to connect: {}".format(e))
      return open_mergerequests

   # return 1 dictionary, for gitlab project_id and mergerequest_id
   def getMergeRequetByID(self, project_id, mergereq_id):
      project = self.gl.projects.get( project_id )
      mergerequest = project.mergerequests.get(mergereq_id)
      return self.getMergeRequetDetails(mergerequest)

   # return 1 dictionary, for gitlab URL
   def getMergeRequetByUrl(self, url):
      url = url.rsplit('/', 4)
      projectpath = "%s/%s" %(url[-4], url[-3])
      project = self.gl.projects.get( projectpath )
      mergerequest = project.mergerequests.get(url[-1])
      return self.getMergeRequetDetails(mergerequest)

   def getDiff(self, project_id, mergereq_id):
      project = self.gl.projects.get( project_id )
      mergerequest = project.mergerequests.get(mergereq_id)
      diffs = mergerequest.diffs.list(all=True)
      for diff in diffs:
         #print(diff.attributes)
         #commits = project.commits.list(since=last_commit)

         last_commit_id = diff.attributes['head_commit_sha'] #'start_commit_sha' 'base_commit_sha'
         commit = project.commits.get(last_commit_id)
         #print(commit.attributes['title'])
         print(commit.attributes['message']) # https://docs.gitlab.com/ee/api/merge_requests.html#get-single-mr-commits

   # not tested yet!!!!
   def updateDiff(self, project_id, mergereq_id, text):
      project = self.gl.projects.get( project_id )
      mergerequest = project.mergerequests.get(mergereq_id)
      diffs = mergerequest.diffs.list(all=True)
      for diff in diffs:
         last_commit_id = diff.attributes['head_commit_sha'] #'start_commit_sha' 'base_commit_sha'
         commit = project.commits.get(last_commit_id)
         commit.attributes['message'] += text
         commit.save()

   # return commit message for project_id (groupname, modulename) and commit_id
   def getCommitMsg(self, project_id, commit_id):
      project = self.gl.projects.get( project_id )
      commit = project.commits.get( commit_id )
      return commit.attributes['message']

   # return project_id
   def getProjectid(self, group, modulename):
      ret = None
      if self.gl:
         try:
            projectpath = group+'/'+modulename
            project = self.gl.projects.get( projectpath )
            ret = project.id
         except Exception as e:
            print(e)
      return ret

   # TODO: add sth. checks ...
   def mergeMergeRequest(self, url):
           
      if self.gl:
         try:
            url = url.rsplit('/', 4)
            projectpath = "%s/%s" %(url[-4], url[-3])
            project = self.gl.projects.get( projectpath )
            mergerequest = project.mergerequests.get(url[-1])
            mergerequest.merge()
            ret = mergerequest['status']
         except Exception as e:
            print("mergeMergeRequest fails with: {}".format(e))

   #  TODO: FIXME:
   #  update MergeRequests, not function yet.
   #
   def updateMergeRequest(self, updateDictionary, URL):
      if self.gl:
         try:
            URL = URL.rsplit('/', 4)
            projectpath = "%s/%s" %(URL[-4], URL[-3])
            project = self.gl.projects.get( projectpath )
            mergerequest = project.mergerequests.get(URL[-1])

            editable_mr = project.mergerequests.get(mergerequest.iid, lazy=True)

            for key, value in updateDictionary.items():
               print("key: {} value: {}".format(key, value))
               if key == 'description':
                  editable_mr.description = value
            editable_mr.save()
            print("saveing done")
         except Exception as e:
            print("update mergeMergeRequest fails with: {}".format(e))
         #mergerequest = project.mergerequests.get(mergereq_id).as_dict()
         #mergerequest['description'] = 'New description'
         #mergerequest['labels'] = ['foo', 'bar']


   # give list of modules in string format []
   def showNumberOfMergeRequests(list_of_modules):
      groups = gl.groups.list(all=True)
      for group in groups:
         projects = group.projects.list(all=True)
         for project in projects:
            for module in list_of_modules:
               if module == project.name:
                  # print(module)
                  mr = project.mergerequests.list(all=True, state="opened")
                  #mr = project.mergerequests.list(all=True)
                  if len(mr) > 0:
                     print('='*20)
                     print('{} MergeRequests for {}'.format(len(mr), module))

   # get by user_id
   def gitlab_get_user_by_name(self, user_name):
       """
       Returns the equvalent user-id of the user-name
       :param: user-name - str
       :return: id - str
       """
       users = self.gl.users.list(username=user_name)
       if len(users)==0:
           return None
       return users[0].id

   def gitlab_get_user_by_id(self, user_id):
       """
       Returns the equvalent user-id of the user-name
       :param: user-name - str
       :return: id - str
       """
       users = self.gl.users.list(user_id)
       if len(users)==0:
           return None
       return users[0].name

   # get MergeRequests for module and filter by user_id
   def getMergequestsURLByUserID(self, url, user_name='<username1>'):
      url = url.rsplit('/', 4)
      projectpath = "%s/%s" %(url[-4], url[-3])
      project = self.gl.projects.get( projectpath )
      u_id = self.gitlab_get_user_by_name(user_name)
      mergerequest = project.mergerequests.get(url[-1], all=True, state="opened", assignee_id=u_id)
      return self.getMergeRequetDetails(mergerequest)

   # get MergeRequests for module and filter by user_id
   def getMergequestsProjectByUserID(self, projectpath='<groupname>/<modulename>', user_names=['<username1>', '<username2>', '<username3>']):
      open_mergerequests = []
      if self.gl:
         try:
            #projectpath = group+'/'+modulename
            for user_name in user_names:
               u_id = self.gitlab_get_user_by_name(user_name)
               project = self.gl.projects.get( projectpath )
               open_mr = project.mergerequests.list(all=True, state="opened", assignee_id=u_id)
               if len(open_mr) > 0:
                  for mergerequest in open_mr:
                     open_mergerequests.append( self.getMergeRequetDetails(mergerequest) )
         except Exception as e:
            print("unable to connect: {}".format(e))
      return open_mergerequests

   #get the members of a gitlab group by groupid
   def getGroupMembersByGroupID(self, groupId):
      #TODO: get the data from the gitlab api   
      lMembers = []
      members = self.gl.groups.get(groupId).members.list(all=True)
      for _ in range(len(members)):
         lMembers.append(members[_].attributes['username'].encode("UTF-8").lower())
      
      return lMembers   



########### ---- Test ----- #############
if __name__ == '__main__':

   obj = GitlabAPI()
   arr = obj.getMergeRequestInformation('raspberry-system/mymodule')
   print("lenght: ",len(arr))
   print("Projekt-ID: ", arr[0]['project_id'])
   print("Merqerequest-ID: ", arr[0]['mr_id'])
   #print("desc: ", arr[0]['description'])

   test = obj.getMergeRequetByID(arr[0]['project_id'], arr[0]['mr_id'])
   print(test['mr_id'])
   print(test['description']) # if this is empty take obj.getDiff(...)

   # get last commit msg
   obj.getDiff(arr[0]['project_id'], arr[0]['mr_id'])
   #obj.updateMergeRequest({}, arr[0]['project_id'], arr[0]['mr_id']) # geht nicht

   #obj.mergeMergeRequest(arr[0]['project_id'], arr[0]['mr_id'])

   print(len(obj.getMergequestsProjectByUserID('<groupname>/<modulename>', user_name="<username>")))
