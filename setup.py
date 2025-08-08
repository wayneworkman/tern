"""Setup configuration for TERN."""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "TERN - AI-powered intelligence for command-line operations"

setup(
    name='tern',
    version='0.1.0',
    description='AI-powered intelligence for command-line operations',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    author='TERN Team',
    python_requires='>=3.8',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=[
        'boto3>=1.26.0',
        'pyyaml>=6.0',
    ],
    entry_points={
        'console_scripts': [
            'tern=tern.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Software Development :: Build Tools',
        'Topic :: System :: Systems Administration',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    keywords='ai bedrock cli command-line devops cloud aws automation',
    project_urls={
        'Bug Reports': 'https://github.com/wayneworkman/tern/issues',
        'Source': 'https://github.com/wayneworkman/tern',
    },
)