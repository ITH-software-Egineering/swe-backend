import os
from uuid import uuid4
from datetime import datetime, timezone
from flask_jwt_extended import get_jwt_identity
from app.utils.helpers import extract_request_data, retrieve_model_info
from app.utils.email_utils import send_email
from app.utils.error_extensions import BadRequest, InternalServerError, NotFound
from app.models.user import Student, Admin
from app.models.module import Module
from app.models.project import Project, StudentProject


def all_students_data():
    students = Student.all()
    students_data = [retrieve_model_info(student, ["id", \
        "first_name", "last_name",\
        "email", "registration_number", "status",\
        "username"])\
        for student in students]
    students_data = list(reversed(students_data))
    return students_data

def count_completed_modules():
    student_id = get_jwt_identity()["id"]
    all_modules = Module.all()
    modules_count = Module.count()
    completed_modules_count = 0
    for module in all_modules:
        projects_count = len(module.projects)
        project_ids = []
        for project in module.projects:
            project_ids.append(project.id)
        completed_projects = StudentProject.count(project_id=tuple(pid for pid in project_ids), student_id=student_id, status=("submitted", "graded", "verified"))
        if projects_count == completed_projects:
            completed_modules_count += 1
    return {"completed": completed_modules_count, "all": modules_count}

def count_completed_projects():
    student_id = get_jwt_identity()["id"]
    completed_projects = StudentProject.count(student_id=student_id, status=("submitted", "graded", "verified"))
    all_projects = Project.count()
    return {"completed": completed_projects, "all": all_projects}

def irelease_next_project(project_id: str):
    student_id = get_jwt_identity()["id"]
    project = Project.search(id=project_id)
    if project is None:
        raise NotFound(f"Project with id {project_id} not found")
    
    if project.next_project_id:
        # Release the next project in the module
        StudentProject(
            student_id=student_id,
            project_id=project.next_project_id,
            status="released"
        ).save()
    else:
        # next_project_id is None therefore release the first project in the next module
        module =  Module.search(id=project.module_id)
        if not module: return
        next_module = module.next_module

        head_project = Project.search(module_id=next_module.id, prev_project_id=None)
        if not head_project: return
        StudentProject(
            student_id=student_id,
            project_id=head_project.id,
            status="released"
        ).save()

def isubmit_student_project(project_id):
    data = extract_request_data("json")
    submission_file = data.get("submission_file")
    student_id = get_jwt_identity()["id"]
    studentProject = StudentProject.search(project_id=project_id, student_id=student_id)
    if not studentProject:
        raise NotFound("Project not found!")
    studentProject.submission_file = submission_file
    studentProject.submitted_on = datetime.now(timezone.utc)
    studentProject.status = "submitted"
    studentProject.save()

def ifetch_current_projects():
    student_id = get_jwt_identity()["id"]
    studentProjects = StudentProject.search(status="released", student_id=student_id)
    projects = []
    if isinstance(studentProjects, list):
        for student_project in studentProjects:
            project = Project.search(id=student_project.project_id)
            if project:
                projects.append(project.to_dict())
    elif isinstance(studentProjects, StudentProject):
        project = Project.search(id=studentProjects.project_id)
        if project:
            projects.append(project.to_dict())
    return projects

def ifetch_project_for_student(project_id):
    student_id = get_jwt_identity()["id"]
    project = Project.search(id=project_id)
    if not project:
        raise NotFound(f"Project with ID {project_id} not found")
    
    studentProject = StudentProject.search(project_id=project_id, student_id=student_id)
    if not studentProject:
        raise NotFound("Project does not exist for this student")
    author = Admin.search(id=project.author_id)
    module = Module.search(id=project.module_id)
    if not author:
        author = "NIL"
    else:
        author = f"{author.first_name} {author.last_name}"
    
    project = project.to_dict()
    project["author"] = author
    project["module"] = module.title
    project["status"] = studentProject.status
    project["grade"] = studentProject.grade

    return project

def ifetch_modules_for_student():
    student_id = get_jwt_identity()["id"]
    mds = Module.all()
    modules = [mod.to_dict() for mod in mds]

    # Release first project if student does not have any project released
    if StudentProject.search(student_id=student_id) is None:
        release_first_project(student_id)
    
    for module in modules:
        projects = jfetch_projects(module.get("id"))
        projects_status = []

        if not projects:
            module["status"] = "locked"
            continue

        for project in projects:
            studentProject = StudentProject.search(student_id=student_id, project_id=project.get("id"))
            if studentProject:
                project["status"] = studentProject.status
            else:
                project["status"] = "locked"
            projects_status.append(project["status"])

        # Set the status of modules based on the status of their projects
        if "released" in projects_status:
            module["status"] = "released"

        if all([s == "locked" for s in projects_status]):
            module["status"] = "locked"

        if all([s == "submitted" or s == "graded" or s == "verified"
                for s in projects_status]):
            module["status"] = "completed"

        module["projects"] = projects

    return modules
    

def jfetch_projects(module_id):
    if module_id:
        projects = Project.search(module_id=module_id)
    else:
        projects = Project.all()

    p_list = []

    if projects:
        if isinstance(projects, list):
            for project in projects:
                p_list.append(project.to_dict())
        else:
            p_list = [projects.to_dict()]
    return p_list

def activate_student_account():
    data = extract_request_data("json")
    email = data.get("email")
    if not email:
        raise BadRequest("Missing required field: email")

    student = Student.search(email=email)
    if not student:
        raise NotFound(f"Student with Email {email} not found")
    
    if isinstance(student, list):
        raise InternalServerError("Multiple students with same email address")
    
    if not (data.get("username") and data.get("password") and data.get("phone")):
        raise BadRequest("Missing required field(s): username, password, phone")

    if student.status == "active":
        raise BadRequest("Account Activated Already!!")

    student.update(**{
        "username": data["username"],
        "password": data["password"],
        "phone": data["phone"],
        "status": "active"
    })
    student_id = student.id
    student.save()
    return student_id
    

def release_first_project(student_id):
    head_module = Module.search(prev_module_id=None)
    if not head_module:
        return

    project = Project.search(prev_project_id=None, module_id=head_module.id)
    if not project:
        return

    StudentProject(
        student_id=student_id,
        project_id=project.id,
        status="released"
    ).save()

def admin_create_new_student():
    data = extract_request_data("json")
    if not (data.get("first_name") and data.get("last_name") and data.get("email")):
        raise BadRequest("Missing required field(s): first_name, last_name, email")
    
    if Student.search(email=data.get("email")) is not None:
        raise BadRequest("Student Account created Already!")
    
    student_count = Student.count() + 1
    registration_number = f"{datetime.now().year}/SWE/C1/{str(student_count).zfill(4)}"
    student_details = {
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "email": data["email"],
        "username": str(uuid4()),
        "password": "placeholder",
        "status": "inactive",
        "registration_number": registration_number
    }
    Student(**student_details).save()
    subject = "Welcome to AuthHub! Activate Your Account Now"
    email_body = f"""
    <html>
    <body>
        <p>Dear {data.get("first_name")},</p>
        <p>Welcome to Authority Innovations Hub in partnership with GDGoC KWASU! We are excited to have you onboard as you begin this journey with us</p>
        <p>Your account has been successfully created by an administrator. To get started, you’ll need to activate your account using the details provided below:</p>
        <p><b>Your Registration Details</b></p>
        <ul>
            <li>Registration Number: {registration_number}</li>
        </ul>
        <p><b>Account Activation</b></p>
        <p>Please click the link below to activate your account:</p>
        <p>
            <a href="{os.getenv("WEB_DOMAIN")}/auth/account/activate">Activate My Account</a>
        </p>
        <p>Once activated, you’ll have full access to your dashboard and all the resources available on our platform.</p>
        <p>If you encounter any issues during the activation process or have any questions, feel free to contact our support team at [{os.getenv("SUPPORT_EMAIL")}].</p>
        <p>We’re thrilled to have you join us and look forward to seeing you succeed!</p>
        <p>Join the whatsapp group here: <a href="https://chat.whatsapp.com/JlyU3TLSs70EWA4atfpSNf">https://chat.whatsapp.com/JlyU3TLSs70EWA4atfpSNf</a></p>
        <p>Join the discord server here: <a href="https://discord.gg/AczjSvv6">https://discord.gg/AczjSvv6</a></p>

        <p>Best regards,</p>
        <p>The AuthHub Team</p>
        <p><a href="https://authhub.tech">https://authhub.tech</a></p>
        <p>{os.getenv("SUPPORT_EMAIL")}</p>
    </body>
    </html>
    """
    send_email(data.get("email"), subject, email_body)