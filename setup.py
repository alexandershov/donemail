from setuptools import find_packages, setup


setup(
    name='donemail',
    author='Alexander Ershov',
    author_email='codumentary.com@gmail.com',
    version='0.1.2',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'donemail = donemail:main'
        ],
    },
    url='https://github.com/alexandershov/donemail',
    keywords=['email', 'notify'],
    classifiers=['Programming Language :: Python :: 2.7'],
)
