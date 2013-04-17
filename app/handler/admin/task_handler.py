#-*- encoding: utf-8 -*-

import tornado.web
import config

from datetime import datetime, timedelta
import admin_base_handler
from common import redis_cache, state, error
from helper import str_helper, http_helper
from proxy import soc_right_proxy
from logic import project_logic, product_logic, task_logic

class TaskListHandler(admin_base_handler.AdminRightBaseHandler):
    _rightKey = config.SOCPMConfig['appCode'] + '.AppManager'
    _right = state.operView

    def _format_project_tasks(self, tasks, isEdit):
        ''' 格式化任务列表。需要格式化 preindex, level '''
        if None == tasks or len(tasks) <= 0:
            tasks = []
            if isEdit:
                tasks.append({'startDate': str_helper.get_now_datestr(), 'endDate': str_helper.get_now_datestr(),
                    'date': 1, 'parentID': 0, 'id': 0, 'preindex': 0, 'sort': 1, 'preID': 0, 'users': '', 
                    'degree': 0, 'userName': '', 'name': '', 'level': 1, 'status': 0, 'userRealName': ''})
            return tasks
        indexMap = {}
        #格式化 statusname，level        
        for task in tasks:
            print task
            if task['parentID'] == 0:
                task['level'] = 1
            else:
                task['level'] = indexMap.get(task['parentID'], {}).get('level', 0) + 1
            indexMap[task['id']] = {'index': task['sort'], 'level':task['level']}
        #格式化 preindex
        temp = []
        for task in tasks:
            if task['preID'] > 0:
                task['preindex'] = indexMap.get(task['preID'], {}).get('index', 0)
            else:
                task['preindex'] = 0
            temp.append(task)
        return temp


    def get(self):
        ps = self.get_page_config('任务列表')
        ps['projects'] = project_logic.ProjectLogic.instance().query_all_by_active()

        if None == ps['projects'] or len(ps['projects']) <= 0:
            ps['projectID'] = 0
            ps['projects'] = []
            ps['tasks'] = []
            ps['msg'] = state.ResultInfo.get(111003, '')
            ps['gotoUrl'] = ps['siteDomain'] + 'Admin/Project/Add'
            self.render('admin/task/list.html', **ps)
            return

        ps['projectID'] = int(self.get_arg('projectID', '0'))
        if ps['projectID'] <= 0:
            ps['projectID'] = ps['projects'][0]['id']

        tasks = task_logic.TaskLogic.instance().query_by_projectID(projectID = ps['projectID'])
        tasks = self._format_project_tasks(tasks, False)
        ps['tasks'] = tasks
        self.render('admin/task/list.html', **ps)

class TaskProjectAddOrEditHandler(TaskListHandler):
    _rightKey = config.SOCPMConfig['appCode'] + '.AppManager'
    _right = 0

    def _init_template_info(self, ps):        
        ps['users'] = soc_right_proxy.get_users_by_usergroup(userGroupID = config.SOCPMConfig['devUserGroupID'])
        ps['projects'] = project_logic.ProjectLogic.instance().query_all_by_active()
        return ps

    def get(self):
        ps = self.get_page_config('编辑任务')
        ps = self._init_template_info(ps)
        
        projectID = int(self.get_arg('projectID', '0'))
        if None == ps['projects'] or len(ps['projects']) <= 0:
            ps['msg'] = state.ResultInfo.get(112006, '')
            ps['gotoUrl'] = ps['siteDomain'] + 'Admin/Project/Add'            
            self.render('admin/task/project_add_or_edit.html', **ps)
            return

        if projectID <= 0:
            projectID = ps['projects'][0]['id']

        tasks = task_logic.TaskLogic.instance().query_by_projectID(projectID = projectID)
        tasks = self._format_project_tasks(tasks, True)
        
        ps['projectID'] = projectID
        ps['tasks'] = tasks
        self.render('admin/task/project_add_or_edit.html', **ps)



    def _format_post_tasks(self, users):
        tasks = []
        index = int(self.get_arg('taskCount', '1')) + 1        
        userMap = {}
        for user in users:
            userMap[user['userName']] = user['userRealName']        
        for i in range(1, index):
            ind = str(i)
            task = {}
            task['sort'] = i
            task['name'] = self.get_arg('task_'+ind, '')
            task['level'] = int(self.get_arg('level_'+ind, '1'))
            task['parentID'] = int(self.get_arg('parentID_'+ind, '0'))
            task['status'] = int(self.get_arg('status_'+ind, '0'))
            task['taskID'] = int(self.get_arg('taskID_'+ind, '0'))
            task['id'] = task['taskID']
            task['date'] = int(self.get_arg('date_'+ind, '1'))
            task['startDate'] = self.get_arg('startDate_'+ind, '')
            task['endDate'] = self.get_arg('endDate_'+ind, '')
            task['preID'] = int(self.get_arg('pre_'+ind, '0'))
            task['preindex'] = task['preID']
            task['degree'] = int(self.get_arg('degree_'+ind, '0'))
            task['userName'] = self.get_arg('user_'+ind, '')
            task['userRealName'] = userMap.get(task['userName'], '')
            task['users'] = self.get_arg('users_'+ind, '')
            tasks.append(task)
        return tasks


    def post(self):
        ps = self.get_page_config('编辑任务')
        ps = self._init_template_info(ps)

        if None == ps['projects'] or len(ps['projects']) <= 0:
            ps['msg'] = state.ResultInfo.get(112006, '')
            ps['gotoUrl'] = ps['siteDomain'] + 'Admin/Project/Add'            
            self.render('admin/task/project_add_or_edit.html', **ps)
            return

        ps['projectID'] = int(self.get_arg('projectID', '0'))
        ps['tasks'] = self._format_post_tasks(users = ps['users'])
        ps['user'] = self.get_oper_user()
        try:
            info = task_logic.TaskLogic.instance().save_tasks(projectID = ps['projectID'], 
                tasks = ps['tasks'], user = ps['user'])

            if info:
                self.redirect(ps['siteDomain'] + 'Admin/Task/List?projectID='+str(ps['projectID']))
                return
            else:
                ps['msg'] = state.ResultInfo.get(101, '')
        except error.RightError as e:
            ps['msg'] = e.msg
        ps = self.format_none_to_empty(ps)
        self.render('admin/task/project_add_or_edit.html', **ps)



class TaskAddOrEditHandler(TaskListHandler):
    _rightKey = config.SOCPMConfig['appCode'] + '.AppManager'
    _right = 0

    def get(self):
        ps = self.get_page_config('编辑任务')        
        
        id = int(self.get_arg('id', '0'))

        if id <= 0:
            ps['msg'] = state.ResultInfo.get(112007, '')
            ps['gotoUrl'] = ps['siteDomain'] + 'Admin/Task/List'            
            self.render('admin/task/edit.html', **ps)
            return

        task = task_logic.TaskLogic.instance().query_one(id = id)        
        ps['task'] = task
        ps = self.format_none_to_empty(ps)
        self.render('admin/task/edit.html', **ps)



    def post(self):
        ps = self.get_page_config('编辑任务')        
        id = int(self.get_arg('id', '0'))
        if id <= 0:
            ps['msg'] = state.ResultInfo.get(112007, '')
            ps['gotoUrl'] = ps['siteDomain'] + 'Admin/Task/List'            
            self.render('admin/task/edit.html', **ps)
            return

        task = self.get_args(['users', 'remark'], '')
        task['id'] = int(self.get_arg('id', '0'))
        task['degree'] = int(self.get_arg('degree', '0'))
        task['projectID'] = int(self.get_arg('projectID', '0'))

        ps['user'] = self.get_oper_user()
        try:
            info = task_logic.TaskLogic.instance().update_degree_remark(
                        id = task['id'], degree = task['degree'], users = task['users'], remark = task['remark'], user = ps['user'])
            if info:
                self.redirect(ps['siteDomain'] + 'Admin/Task/List?projectID='+str(task['projectID']))
                return
            else:
                ps['msg'] = state.ResultInfo.get(101, '')
        except error.RightError as e:
            ps['msg'] = e.msg
        ps = self.format_none_to_empty(ps)
        self.render('admin/task/edit.html', **ps)



class TaskDetailHandler(admin_base_handler.AdminRightBaseHandler):
    _rightKey = config.SOCPMConfig['appCode'] + '.AppManager'
    _right = state.operView

    def get(self):
        ps = self.get_page_config('任务详情')
        id = int(self.get_arg('id', '0'))
        task = task_logic.TaskLogic.instance().query_one(id = id)
        if None == task:
            ps['msg'] = state.ResultInfo.get(112007, '')
            ps['gotoUrl'] = ps['siteDomain'] + 'Admin/Task/List'
            product = {'id':'','name':'','teamPath':'','productUserName':'','productUserRealName':'',
                            'devUserName':'','devUserRealName':'', 'startDate':'', 'endDate':''
                            ,'remark':'','status':1,'creater':'', 
                            'createTime':'','lastUpdater':'','lastUpdateTime':'', 'projects':[]}
        project['projects'] = product_logic.ProductLogic.instance().query_all_by_project(project['id'])
        ps['project'] = project
        self.render('admin/project/detail.html', **ps)