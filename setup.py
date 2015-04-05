from setuptools import find_packages, setup


setup(
    name='donemail',
    author='Alexander Ershov',
    version='0.1.0',
    packages=find_packages(),
    tests_require=[
        'mock',
        'pytest',
    ],
    entry_points={
        'console_scripts': [
            'donemail = donemail:main'
        ],
    },
)
