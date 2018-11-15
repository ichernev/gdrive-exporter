import httplib2
import os
import sys
import io

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from googleapiclient.http import MediaIoBaseDownload

# try:
#     import argparse
#     flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
# except ImportError:
#     flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive.readonly' # 'https://www.googleapis.com/auth/drive.metadata.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'CLI'


def gmt(x):
    return 'application/vnd.google-apps.' + x


class MIME_TYPES(object):
    DIR = gmt('folder')
    DOCUMENT = gmt('document')
    SHEET = gmt('spreadsheet')
    PRESENTATION = gmt('presentation')
    DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    PDF = 'application/pdf'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def list_dir(drive_service, dir_id):
    page_token = None
    res = []
    while True:
        response = drive_service.files().list(q="'%s' in parents" % dir_id,
                                              spaces='drive',
                                              fields='nextPageToken, files(id, name, mimeType)',
                                              pageToken=page_token).execute()
        for file in response.get('files', []):
            # Process change
            # print 'Found file: %s (%s)' % (file.get('name'), file.get('id'))
            res.append([file.get('name'), file.get('id'), file.get('mimeType')])

        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break

    return res

def export_file(drive_service, file_id, mime_type, dest):
    # file_id = '1ZdR3L3qP4Bkq8noWLJHSr_iBau0DNT4Kli4SxNc2YEo'
    request = drive_service.files().export_media(fileId=file_id,
                                                 mimeType=mime_type)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()

    with open(dest, 'wb') as f:
        f.write(fh.getvalue())
    fh.close()


def get_by_path(drive_service, path):
    if path == '/' or path == '':
        return ['My Drive', 'root', MIME_TYPES.DIR]

    path = path.split('/')

    if len(path) == 0:
        return None
    if len(path[0]) == 0:
        path = path[1:]

    current_dir_id = 'root'
    failed_on = None
    last_item = None
    for i, path_comp in enumerate(path):
        response = drive_service.files().list(
            q="'%s' in parents and name = '%s'" % (current_dir_id, path_comp),
            spaces='drive',
            fields='files(id, name, mimeType)',
            pageToken=None).execute()

        files = response.get('files', [])
        if len(files) != 1:
            failed_on = path_comp
            break
        last_item = files[0]
        last_item = [last_item.get('name'), last_item.get('id'), last_item.get('mimeType')]
        current_dir_id = last_item[1]

    if failed_on:
        raise Exception("failed on %s" % failed_on)

    return last_item


def sync(drive_service, path_id, destination):
    print("SYNC %s" % destination)
    entries = list_dir(drive_service, path_id)
    for entry in entries:
        if entry[0] in ['Resume-dev']:
            print("WTF %s" % entry[0])
            continue
        if entry[2] == MIME_TYPES.DIR:
            inner_dest = os.path.join(destination, entry[0])
            os.makedirs(inner_dest, exist_ok=True)
            sync(drive_service, entry[1], inner_dest)
        elif entry[2] == MIME_TYPES.DOCUMENT:
            inner_dest = os.path.join(destination, entry[0] + '.docx')
            if os.path.exists(inner_dest):
                print("EX %s" % inner_dest)
            else:
                print("EXP DOCX %s" % inner_dest)
                export_file(drive_service, entry[1], MIME_TYPES.DOCX, inner_dest)
        elif entry[2] == MIME_TYPES.SHEET:
            inner_dest = os.path.join(destination, entry[0] + '.xlsx')
            if os.path.exists(inner_dest):
                print("EX %s" % inner_dest)
            else:
                print("EXP XLSX %s" % inner_dest)
                export_file(drive_service, entry[1], MIME_TYPES.XLSX, inner_dest)
        elif entry[2] == MIME_TYPES.PRESENTATION:
            inner_dest = os.path.join(destination, entry[0] + '.pdf')
            if os.path.exists(inner_dest):
                print("EX %s" % inner_dest)
            else:
                print("EXP PDF %s" % inner_dest)
                export_file(drive_service, entry[1], MIME_TYPES.PDF, inner_dest)
        else:
            print("SKIP %s / %s" % (os.path.join(destination, entry[0]), entry[2]))


def main(args):
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    # res = list_dir(service, 'root')

    # res = list_dir(service, '0ByParG_FsTEENGE4NTkwMWEtN2VmZS00YTVmLThhNGUtODc0NTAwN2I5ZDcz')

    # print("%s" % "\n".join(map(str, res[:10])))
    # export_file(service, '1YmaO-anDRs_rOcNHL_9mT-HuFyuuIcg6wtlLzjr-PVg', 'application/pdf', '/Users/iskren/Downloads/exported2.pdf')

    # export_file(service,
    #             '1YmaO-anDRs_rOcNHL_9mT-HuFyuuIcg6wtlLzjr-PVg',
    #             'application/vnd.oasis.opendocument.text',
    #             '/Users/iskren/Downloads/exported3.odt')

    # print(get_by_path(service, args[0]))

    if len(args) != 2:
        print("G_DRIVE_DIR TARGET_DIR")

    os.makedirs(args[1], exist_ok=True)
    sync(service, get_by_path(service, args[0])[1], args[1])

    # results = service.files().list(
    #     pageSize=10,fields="nextPageToken, files(id, name)").execute()
    # items = results.get('files', [])
    # if not items:
    #     print('No files found.')
    # else:
    #     print('Files:')
    #     for item in items:
    #         print('{0} ({1})'.format(item['name'], item['id']))

if __name__ == '__main__':
    main(sys.argv[1:])
