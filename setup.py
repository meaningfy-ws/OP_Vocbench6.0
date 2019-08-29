from setuptools import setup, find_packages

setup(
    name='VBController',
    version='1.0dev',
    packages=find_packages(),
    package_data={'':['requirements.txt','README.md', 'setup.cfg']},
    url='http://publications.europa.eu',
    maintainer='Sebastien Albouze',
    maintainer_email='sebastien.albouze@ext.publications.europa.eu',
    license='MIT',
    long_description=open('./VBController/README.md').read(),
)