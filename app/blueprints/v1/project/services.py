from datetime import datetime, timezone

from flask_jwt_extended import get_jwt_identity

from app.models.module import Module
from app.models.project import Project, StudentProject
from app.utils.helpers import extract_request_data
from app.utils.error_extensions import BadRequest, NotFound
from app.models.user import Admin, Student


def igrade_student_project():
    data = extract_request_data("json")
    mentor_id = get_jwt_identity()["id"]

    if not data.get("student_project_id") or not data.get("grade"):
        raise BadRequest("Required field(s): student_project_id, grade not present")

    studentProject = StudentProject.search(id=data.get("student_project_id"))
    if not studentProject:
        raise NotFound("Student's project not found")
    
    studentProject.status = "graded"
    studentProject.graded_on = datetime.now(timezone.utc)
    studentProject.graded_by = mentor_id
    studentProject.grade = data.get("grade")
    studentProject.feedback = data.get('feedback')
    studentProject.save()

def iretrieve_projects_with_submissions():
    submissions = StudentProject.search(status="submitted")
    if not submissions:
        raise NotFound("No Submitted Projects Found")

    """Check how many projects were found"""
    if isinstance(submissions, StudentProject):
        submissions = [submissions]

    projects_with_submissions = []
    projects_with_submissions_registry = []
    for submission in submissions:
        if submission.project_id in projects_with_submissions_registry:
            continue
        project = Project.search(id=submission.project_id)
        if not Project: continue
        projects_with_submissions_registry.append(project.id)
        projects_with_submissions.append(project.to_dict())

    return projects_with_submissions


def iretrieve_assigned_project_submissions(project_id):
    mentor_id = get_jwt_identity()["id"]
    project = Project.search(id=project_id)
    assigned_pjts = StudentProject.search(status="submitted", project_id=project_id, assigned_to=mentor_id)

    if not assigned_pjts:
        raise NotFound("No submitted projects")

    tmp = []
    if isinstance(assigned_pjts, StudentProject):
        tmp.append(assigned_pjts)
    elif isinstance(assigned_pjts, list):
        for pjt in assigned_pjts:
            tmp.append(pjt)

    assigned_projects = {
        "project": project.to_dict(),
        "data": [],
    }
    for t in tmp:
        student = Student.search(id=t.student_id)
        data = {
            "student": student.to_dict(),
            "student_project": t.to_dict(),
        }
        assigned_projects.get("data").append(data)
    return assigned_projects

def igenerate_project_submission(project_id):
    mentor_id = get_jwt_identity()["id"]
    submitted_projects = StudentProject.search(project_id=project_id, status="submitted", assigned_to=None)
    if not submitted_projects:
        raise NotFound("No Submitted Projects")

    """Check how many projects were found"""
    if isinstance(submitted_projects, StudentProject):
        submitted_projects.assigned_to = mentor_id
        submitted_projects.save()
    elif isinstance(submitted_projects, list):
        submitted_projects[0].assigned_to = mentor_id
        submitted_projects[0].save()

def ifetch_project(project_id):
    project = Project.search(id=project_id)
    if not project:
        raise NotFound(f"Project with ID {project_id} not found")
    
    author = Admin.search(id=project.author_id)
    module = Module.search(id=project.module_id)
    if not author:
        author = "NIL"
    else:
        author = f"{author.first_name} {author.last_name}"

    project = project.to_dict()
    project["author"] = author
    project["module"] = module.title

    return project

def fetch_projects():
    module_id = extract_request_data("args").get('module_id')

    if module_id:
        projects = Project.search(module_id=module_id)
    else:
        projects = Project.all()

    p_list = []

    if not projects or projects is None:
        raise NotFound("No projects found")

    if isinstance(projects, list):
        for project in projects:
            p_list.append(project.to_dict())
    elif isinstance(projects, Project):
        p_list = [projects.to_dict()]
    return p_list

def create_new_project():
    data = extract_request_data("json")

    # fetch status, module_id, author_id, and prev_project_id
    status = "draft"
    if data.get("mode") == "publish": status = "published"
    data["author_id"] = get_jwt_identity()["id"]
    data["status"] = status
    
    Project(**data).save()

def update_single_project_details(project_id):
    data = extract_request_data("json")
    project = Project.search(id=project_id)
    if project is None or isinstance(project, list):
        raise BadRequest("Project not found or multiple projects found")
    
    status = "draft"
    if data.get("mode") == "publish": status = "published"
    data["status"] = status
    data["author_id"] = get_jwt_identity()["id"]

    project.update(**data)
    project.save()














def _retrieve_projects_status():
    data = extract_request_data("json")
    projects_ids = data.get("projects")
    student_id = data.get("student_id")
    statuses = []
    for p_id in projects_ids:
        student_project = StudentProject.search(student_id=student_id, project_id=p_id)

        if student_project and not isinstance(student_project, list):
            statuses.append({
                "id": p_id,
                "status": student_project.status,
            })
        else:
            statuses.append({
                "id": p_id,
                "status": "unreleased",
            })
    return {"statuses": statuses}

def mark_a_project_as_done():
    data = extract_request_data("json")
    student_id = data.get("student_id")
    project_id = data.get("project_id")

    project = Project.search(id=project_id)

    student_project = StudentProject.search(project_id=project_id, student_id=student_id)
    if student_project is not None and not isinstance(student_project, list):
        student_project.status = "completed"
        student_project.save()
    else:
        if project and not isinstance(project, list):
            student_project = StudentProject(student_id=student_id, project_id=project_id, status="completed")
            student_project.save()
        else:
            raise BadRequest(f"Project does not exist or there are multiple entries for project with id {project_id}")

    if project.next_project:
        if not StudentProject.search(student_id=student_id, project_id=project.next_project_id):
            new_student_project = StudentProject(student_id=student_id, project_id=project.next_project_id, status="pending")
            new_student_project.save()

def sort_projects(projects):
    temp_1 = {}
    p_list = []

    # Retrieve the head of the linked list
    project_head = get_project_head(projects)
    if project_head is None: return []
    p_list.append(project_head)

    # Add the projects to a dictionary
    #   for easier retrieval during sorting
    for project in projects:
        if project.id != project_head.id:
            temp_1[project.id] = project

    # retrieve the next project from the
    # dictionary based on the next_project_id value
    temp_2 = project_head
    while temp_2.next_project_id is not None:
        p_id = temp_2.next_project_id
        temp_2 = temp_1.get(p_id)
        p_list.append(temp_2)
        del temp_1[p_id]

    # Append the remaining unorganized projects to the returned output
    for value in temp_1.values():
        p_list.append(value)

    return p_list

def get_project_head(projects):
    for project in projects:
        if project.prev_project_id == None:
            return project
    return None