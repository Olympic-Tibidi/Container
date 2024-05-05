import streamlit as st
import pandas as pd
from google.cloud import storage
import io
import json
import pickle


st.set_page_config(layout="wide")
target_bucket="new_suzano_spare"
utc_difference=7
owner_codes= pickle.load(open("owner_codes.dat", "rb"))
letter_dict= pickle.load(open("bic_letters.dat", "rb"))



def gcp_download(bucket_name, source_file_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_file_name)
    data = blob.download_as_text()
    return data
def gcp_download_new(bucket_name, source_file_name):
    conn = st.connection('gcs', type=FilesConnection)
    a = conn.read(f"{bucket_name}/{source_file_name}", ttl=600)
    return a
def gcp_download_x(bucket_name, source_file_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_file_name)
    data = blob.download_as_bytes()
    return data

def gcp_csv_to_df(bucket_name, source_file_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_file_name)
    data = blob.download_as_bytes()
    df = pd.read_csv(io.BytesIO(data),index_col=None)
    print(f'Pulled down file from bucket {bucket_name}, file name: {source_file_name}')
    return df


def upload_cs_file(bucket_name, source_file_name, destination_file_name): 
    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(destination_file_name)
    blob.upload_from_filename(source_file_name)
    return True
    
def upload_json_file(bucket_name, source_file_name, destination_file_name): 
    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(destination_file_name)
    blob.upload_from_filename(source_file_name,content_type="application/json")
    return True
def upload_xl_file(bucket_name, uploaded_file, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    uploaded_file.seek(0)

    # Upload the file from the file object provided by st.file_uploader
    blob.upload_from_file(uploaded_file)

def list_cs_files(bucket_name): 
    storage_client = storage.Client()

    file_list = storage_client.list_blobs(bucket_name)
    file_list = [file.name for file in file_list]

    return file_list

def list_cs_files_f(bucket_name, folder_name):
    storage_client = storage.Client()

    # List all blobs in the bucket
    blobs = storage_client.list_blobs(bucket_name)

    # Filter blobs that are within the specified folder
    folder_files = [blob.name for blob in blobs if blob.name.startswith(folder_name)]

    return folder_files

def list_files_in_folder(bucket_name, folder_name):
    storage_client = storage.Client()
    blobs = storage_client.list_blobs(bucket_name, prefix=folder_name)

    # Extract only the filenames without the folder path
    filenames = [blob.name.split("/")[-1] for blob in blobs if "/" in blob.name]

    return filenames

def list_files_in_subfolder(bucket_name, folder_name):
    storage_client = storage.Client()
    blobs = storage_client.list_blobs(bucket_name, prefix=folder_name, delimiter='/')

    # Extract only the filenames without the folder path
    filenames = [blob.name.split('/')[-1] for blob in blobs]



bill_data=gcp_download(target_bucket,rf"terminal_bill_of_ladings.json")
admin_bill_of_ladings=json.loads(bill_data)


def guess_missing_number(container):
    
    liste=[i for i in container]
    a=0
    b=0
    
    def calculate_letters(a):
        for i,j in enumerate([k for k in container][:4]):
            a+=(2**i)*letter_dict[j]
        return a
   
    
    def figure_letter(a,b):
    
        for i,j in enumerate([k for k in container][:4]):
            if j=='?':
                #print(i)
                unknown_index=i
                #print(unknown_index)
                unknown_calculation=2**(unknown_index)
                #print(unknown_calculation)
            else:
                z=2**(i)
                a+=(int(z)*int(letter_dict[j]))
        #print(f'a is {a}')
        x=0
        pos=[]
        for q in letter_dict.keys():
            #print(q)
            m=(2**unknown_index)*letter_dict[q]-(int(((2**unknown_index)*letter_dict[q]+a+b)/11)*11)-(int(container[-1])-a-b)
            if m ==0:
                pos.append(q)
        if unknown_index==3 and "U" in pos:
            pos=["U"]
        return pos
    
    def calculate_number(b):
        for i,j in enumerate([k for k in container][4:-1]):
            z=2**(i+4)
            b+=(int(z)*int(j))
        return b
    
    def figure_number(a,b):
    
        for i,j in enumerate([k for k in container][4:-1]):
            if j=='?':
                #print(i)
                unknown_index=i+4
                #print(unknown_index)
                unknown_calculation=2**(unknown_index)
                #print(unknown_calculation)
            else:
                z=2**(i+4)
                b+=(int(z)*int(j))
        #print(f'b is {b}')
        x=0
        for q in range(10):
            m=(2**unknown_index)*q-(int(((2**unknown_index)*q+a+b)/11)*11)-(int(container[-1])-a-b)
            if m ==0:
                return q
            
    if '?' not in container:
        return check_container_no(container)
    if '?' in container[4:-1]:
        a=0
        b=0
        a=calculate_letters(a)
        target=figure_number(a,b)
    if '?' in container[:4]:
        target_pool=[]
        a=0
        b=0
        b=calculate_number(b)
        pos=figure_letter(a,b)
        for i in pos:
            possibility=container.replace('?',str(i))
            if check_container_no(possibility)=='Container Number Legitimate':
                target_pool.append(i)
            else:
                continue
        target=target_pool
        if target==['U']:
            target='U'
            
        print(f'target pool is {target}')
        
        trial=container
        print(trial)
        for i in target:
            z=trial.replace('?',str(i))
            #print(z)
            if z[:3] not in owner_codes:
                target.remove(i)
                
    if container[-1]=='?':
        b=0      
        n=calculate_number(b)
        a=0
        l=calculate_letters(a)
        target=n+l-(int((n+l)/11)*11)
    if type(target) is list:
        return target, [container.replace('?',str(i)) for i in target]
        
    return target,container.replace('?',str(target))


st.title('Container Number Validation')
container = st.text_input('Enter the container number:', '')
if st.button('Check Validity'):
    if check_container_no(container):
        st.success('Container Number is Legitimate')
    else:
        st.error('Container Number is Wrong')
