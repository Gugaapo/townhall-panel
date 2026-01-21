import asyncio
import logging
from datetime import datetime

from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.department_repository import DepartmentRepository
from app.core.security import get_password_hash
from app.utils.constants import UserRole, DepartmentType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_departments():
    """Seed initial departments"""
    dept_repo = DepartmentRepository()

    departments = [
        {
            "name": "Administration",
            "code": "ADM",
            "type": DepartmentType.MAIN.value,
            "description": "Main administration department - handles document routing",
            "is_active": True,
            "created_at": datetime.utcnow()
        },
        {
            "name": "Education",
            "code": "EDU",
            "type": DepartmentType.REGULAR.value,
            "description": "Education department",
            "is_active": True,
            "created_at": datetime.utcnow()
        },
        {
            "name": "Sports",
            "code": "SPO",
            "type": DepartmentType.REGULAR.value,
            "description": "Sports and recreation department",
            "is_active": True,
            "created_at": datetime.utcnow()
        },
        {
            "name": "Health",
            "code": "HEA",
            "type": DepartmentType.REGULAR.value,
            "description": "Health department",
            "is_active": True,
            "created_at": datetime.utcnow()
        },
        {
            "name": "Finance",
            "code": "FIN",
            "type": DepartmentType.REGULAR.value,
            "description": "Finance and budget department",
            "is_active": True,
            "created_at": datetime.utcnow()
        },
    ]

    for dept in departments:
        # Check if department already exists
        existing = await dept_repo.find_by_code(dept["code"])
        if existing:
            logger.info(f"Department {dept['name']} ({dept['code']}) already exists")
            continue

        # Create department
        created = await dept_repo.create(dept)
        logger.info(f"Created department: {created['name']} ({created['code']})")

    return await dept_repo.find_active_departments()


async def seed_admin_user(departments: list):
    """Seed initial admin user"""
    user_repo = UserRepository()

    # Find the main administration department
    admin_dept = next(
        (d for d in departments if d.get("type") == DepartmentType.MAIN.value),
        None
    )

    if not admin_dept:
        logger.error("Main administration department not found!")
        return

    admin_email = "admin@townhall.com"

    # Check if admin already exists
    existing = await user_repo.find_by_email(admin_email)
    if existing:
        logger.info(f"Admin user {admin_email} already exists")
        return

    # Create admin user
    admin_user = {
        "email": admin_email,
        "password_hash": get_password_hash("admin123"),  # Default password
        "full_name": "System Administrator",
        "department_id": admin_dept["_id"],
        "role": UserRole.ADMIN.value,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    created = await user_repo.create(admin_user)
    logger.info(f"Created admin user: {created['email']}")
    logger.info("=" * 50)
    logger.info("IMPORTANT: Default admin credentials:")
    logger.info(f"  Email: {admin_email}")
    logger.info(f"  Password: admin123")
    logger.info("  Please change this password after first login!")
    logger.info("=" * 50)


async def seed_sample_users(departments: list):
    """Seed sample users for each department"""
    user_repo = UserRepository()

    # Sample users for each department
    sample_users = []

    for dept in departments:
        if dept.get("type") == DepartmentType.MAIN.value:
            # Administration department
            sample_users.append({
                "email": f"head.admin@townhall.com",
                "password_hash": get_password_hash("password123"),
                "full_name": "John Smith",
                "department_id": dept["_id"],
                "role": UserRole.DEPARTMENT_HEAD.value,
                "is_active": True,
            })
            sample_users.append({
                "email": f"clerk.admin@townhall.com",
                "password_hash": get_password_hash("password123"),
                "full_name": "Jane Doe",
                "department_id": dept["_id"],
                "role": UserRole.EMPLOYEE.value,
                "is_active": True,
            })
        else:
            # Other departments
            dept_code = dept["code"].lower()
            sample_users.append({
                "email": f"head.{dept_code}@townhall.com",
                "password_hash": get_password_hash("password123"),
                "full_name": f"{dept['name']} Head",
                "department_id": dept["_id"],
                "role": UserRole.DEPARTMENT_HEAD.value,
                "is_active": True,
            })
            sample_users.append({
                "email": f"employee.{dept_code}@townhall.com",
                "password_hash": get_password_hash("password123"),
                "full_name": f"{dept['name']} Employee",
                "department_id": dept["_id"],
                "role": UserRole.EMPLOYEE.value,
                "is_active": True,
            })

    # Create users
    for user in sample_users:
        existing = await user_repo.find_by_email(user["email"])
        if existing:
            logger.info(f"User {user['email']} already exists")
            continue

        created = await user_repo.create(user)
        logger.info(f"Created user: {created['email']} ({created['role']} in {created['department_id']})")


async def seed_database():
    """Main seed function"""
    try:
        await connect_to_mongo()
        logger.info("Starting database seeding...")

        # Seed departments
        logger.info("\n--- Seeding Departments ---")
        departments = await seed_departments()

        # Seed admin user
        logger.info("\n--- Seeding Admin User ---")
        await seed_admin_user(departments)

        # Seed sample users
        logger.info("\n--- Seeding Sample Users ---")
        await seed_sample_users(departments)

        logger.info("\n=== Database seeding completed successfully! ===")
        logger.info("\nYou can now log in with:")
        logger.info("  Admin: admin@townhall.com / admin123")
        logger.info("  Sample users: head.<dept>@townhall.com / password123")
        logger.info("  (e.g., head.edu@townhall.com, employee.spo@townhall.com)")

    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        raise
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(seed_database())
