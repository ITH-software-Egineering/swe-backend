from flask import Blueprint
from app.blueprints.v1.student.controllers import activate_account, countCompleted, fetch_modules_for_student, fetchproject
from app.blueprints.v1.student.controllers import fetchcurrentprojects, submitProject, create_new_student, all_students

student_bp = Blueprint('student', __name__)

# Admin and Mentor access only functionalities
student_bp.add_url_rule("/create", view_func=create_new_student, methods=["POST"])
student_bp.add_url_rule("/all", view_func=all_students, methods=["GET"])

# Student Functionalities
student_bp.add_url_rule('/account/activate', view_func=activate_account, methods=['POST'])
student_bp.add_url_rule('/modules', view_func=fetch_modules_for_student, methods=['GET'])
student_bp.add_url_rule('/project/<project_id>', view_func=fetchproject, methods=['GET'])
student_bp.add_url_rule('/projects/current', view_func=fetchcurrentprojects, methods=['GET'])
student_bp.add_url_rule('/count/completed', strict_slashes=False, view_func=countCompleted, methods=["GET"])
student_bp.add_url_rule('/project/<project_id>/submit', view_func=submitProject, methods=['POST'])