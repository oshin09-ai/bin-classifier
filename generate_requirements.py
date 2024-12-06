import pkg_resources
import subprocess

def generate_requirements():
    packages = [
        'flask>=2.0.0',
        'elasticsearch>=8.0.0',
        'openai>=1.0.0',
        'python-dotenv>=1.0.0',
        'werkzeug>=2.0.0',
        'requests>=2.0.0',
        'Pillow>=10.0.0',
        'typing-extensions>=4.7.0',
        'jinja2>=3.1.2',
        'itsdangerous>=2.2.0',
        'blinker>=1.9.0'
    ]
    
    with open('requirements.txt', 'w') as f:
        for package in packages:
            f.write(f"{package}\n")

if __name__ == "__main__":
    generate_requirements()
