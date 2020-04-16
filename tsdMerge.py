import tsdgit
import helper
from helper import bcolors as bc
from vitools import viToolsHelper
import logging
logging.basicConfig(filename='alles.log',level=logging.INFO)

#
#  git_work_path := The path where all your git Repositories are
#
class tsdMerge():
   def __init__(self, config=None, args=[], kwargs={}):
      self.args = args
      self.kwargs = kwargs
      #self.work_path = git_work_path
      self.vihelper = viToolsHelper(config)
      self.gitObj = self.vihelper.gtools


   #
   # checkout_branch := Start-Branch in den ff-gemerged werden soll,
   # ff_forward_branch := Ziel-Branch von dem ff-forward gemered werden soll
   #
   def mergeListOfRepos(self, list_repos, checkout_branch='master', ff_forward_branch='origin/develop', logging=True, question=True, options=[]):
      read_check_branch = checkout_branch
      read_ff_branch = ff_forward_branch
      if 'origin/' not in read_check_branch:
         checkout_branch = 'origin/' + read_check_branch
      if 'origin/' not in read_ff_branch:
         checkout_branch = 'origin/' + read_ff_branch

      ret = {'retCode':0, 'stdout':'', 'stderr':''}
      for module in list_repos:
         if logging is True:
            print (bc.WARNING + "ff-Merge: %s   %s --> %s" + bc.ENDC) %(module, checkout_branch, ff_forward_branch)
            print("Commits:")
            print(self.gitObj.getLog(module, checkout_branch, ff_forward_branch, "%h, %cd, %cn, %s", ['--first-parent', "--date=format:'%a %d-%m-%Y %R'"])['stdout'])

         if (question is False) or (helper.query_yes_no("Do you want to ff-merge: %s" %(module), 'no') == 'yes'):
            ret = self.gitObj.mergeRepo(module, read_check_branch, read_ff_branch, options)
            if 'retCode' in ret:
               if ret['retCode'] == 128:
                  print(bc.FAIL + "ff-Merge not possible: %s   %s --> %s\nMerge Commit only" + bc.ENDC) %(module, checkout_branch, ff_forward_branch)
         else:
            ret = {'retCode':-1, 'stdout':'no', 'stderr': ''}

         if (logging is True) and (ret['retCode'] == 0):
            output_string = module + '\n'
            output_string += self.gitObj.getLog(module, checkout_branch, ff_forward_branch, '%H', ['--first-parent'])['stdout']
            output_string += '\n'
            with open('history_merge.txt', 'a') as the_file:
               the_file.write( output_string )

      return ret


   #
   # reset_branch := Branch zu dem resetet werden soll
   # wird gegen lokalen HEAD vom aktuellen Branch vergleichen falls Unterschiede bestehen
   #
   def resetListOfRepos(self, list_repos, reset_branch='origin/master', logging=True, question=True, options=[]):
      for module in list_repos:
         if logging == True:
            self.gitObj.log.info("=====================")
            self.gitObj.log.info("reset Module: {} --> {}".format(module,reset_branch))
            self.gitObj.log.info("Commits will be discarded:")
            #self.gitObj.log.info( self.gitObj.getLog(module, 'HEAD', reset_branch, '%H', ['--first-parent'])['stdout'] )
            self.gitObj.log.info( self.gitObj.getLog(module, reset_branch, 'HEAD', '%H', ['--graph', '--oneline', '--decorate'])['stdout'] )
         if question == True:
            if (helper.query_yes_no("Do you want to reset: %s" %(module),  'no') == 'yes'):
               self.gitObj.resetRepo(module, reset_branch, options)
               self.gitObj.log.info("Module: {} reseted to Branch: {}".format(module,reset_branch))
               #self.gitObj.log.info( self.gitObj.getLog(module, reset_branch, 'HEAD', '%H', ['--graph', '--oneline', '--decorate'])['stdout'] )
         elif question == False:
            self.gitObj.resetRepo(module, reset_branch, options)
            self.gitObj.log.info("Module: {} reseted to Branch: {}".format(module,reset_branch))
         else:
            self.gitObj.log.warning("wrong use of logging Parameter. Must be True or False")

   #
   # push modules
   #
   def pushListOfRepos(self, list_repos, logging=True, question=True, options=[]):
      for module in list_repos:
         if (question == False) or (helper.query_yes_no("\nDo you want to push: %s" %(module),  'no') == 'yes'):
            ret = self.gitObj.pushRepo(module, options)
         else:
            ret = {'retCode':-1, 'stdout':'no', 'stderr': ''}
         if (logging is True) and (ret['retCode'] == 0):
            self.gitObj.log.info("Module: {} pushed.".format(module))

   #
   # check if missing commits develop_release_candidate and develop
   #
   def checkDevelop(self, list_repos, checkout_branch='origin/develop_release_candidate', ff_forward_branch='origin/develop'):
      check_liste = []
      retCode = 0
      for module in list_repos:
         #print(module)
         retCode = self.gitObj.getLog(module, checkout_branch, ff_forward_branch, '%H', ['--first-parent'])['retCode']
         if retCode != 128:
            ret = self.gitObj.getLog(module, checkout_branch, ff_forward_branch, '%H', ['--first-parent'])['stdout']
            if ret == "":
               reverse = self.gitObj.getLog(module, ff_forward_branch, checkout_branch, '%H', ['--first-parent'])['stdout']
               if reverse != "":
                  self.gitObj.log.warning("%s -> %s" %(ff_forward_branch, checkout_branch))
                  self.gitObj.log.info("Unterschied in module: %s with: %s" %(module, ret))

            elif ret != "":
               self.gitObj.log.warning("%s -> %s" %(checkout_branch, ff_forward_branch))
               self.gitObj.log.info("Unterschied in module: %s with: %s" %(module, ret))

            else:
               pass
         #else

   #
   # check if sync neceassry between develop_release_candidate and develop
   #
   def syncDevelop(self, list_repos, checkout_branch='develop_release_candidate', ff_forward_branch='develop', logging=True, question=True):
      for module in list_repos:
         print(module)
         #self.gitObj.updateModuleRepo(module)
         self.gitObj.fetchRepo(self.gitObj.workdir + module)

         ret = self.gitObj.getLog(module, "origin/" + checkout_branch, "origin/" + ff_forward_branch, '%H', ['--first-parent'])
         if (ret['retCode'] != 128):
            if (ret['stdout'] == ''):
               tmp = checkout_branch
               checkout_branch = ff_forward_branch
               ff_forward_branch = tmp
               ret = self.gitObj.getLog(module, "origin/" + checkout_branch, "origin/" + ff_forward_branch, '%H', ['--first-parent'])
            if (ret['stdout'] != ''):
               ret = self.mergeListOfRepos([module], checkout_branch, "origin/" + ff_forward_branch, logging, question)
               if ret['retCode'] == 0:
                  self.pushListOfRepos([module], logging=True, question=True)
         else:
            self.gitObj.log.error("%s: \n%s" %(module, ret['stderr']))



if __name__ == "__main__":
   obj = tsdMerge()
   print "test"
  

   all_modules = obj.vihelper.CONFIG.mconfig.getModuleList(['system'], ['lib', 'api', 'comp'], 0, False)

