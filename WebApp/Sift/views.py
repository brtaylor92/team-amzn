from django.shortcuts import render, get_object_or_404
from Sift.models import Cluster, Post, ClusterWord, StopWord
from django.http import HttpResponseRedirect
# from postmarkup import render_bbcode
from lxml import html
from bs4 import BeautifulSoup
from django.core.cache import cache

import os

import time
import Sift.clustering
import Sift.Notification
import Sift.tasks as tasks
import Sift.forms
from Sift.models import ClusterRun
from Sift.forms import StopwordDelete, StopwordAdd


def general(request):
    headline = "General Analytics"
    trendingClusters = Cluster.objects.filter(ispinned=0)
    pinnedClusters = Cluster.objects.filter(ispinned=1)


    pieData = [['Forum ID', 'Number of Posts']]
    for cluster in trendingClusters:
        pieData.append([cluster.name, Post.objects.filter(cluster=cluster.clusterid).count()])

    lineClusterNames = []

    for cluster in trendingClusters:
        lineClusterNames.append(cluster.name)

    lineDates = []
    lineData = {}
    posts = Post.objects.values('creation_date', 'cluster').order_by('creation_date')
    for post in posts:
        id = post["cluster"]
        if (id != None):
            date = int(time.mktime(post["creation_date"].timetuple())) * 1000
            try:
                if date in lineData:
                    lineData[date][id-1] += 1
                else:
                    lineData[date] = [0] * len(lineClusterNames)
                    lineData[date][id-1] = 1
                    lineDates.append(date)
            except:
                pass

    context = {'pinnedClusters': pinnedClusters, 'trendingClusters':
               trendingClusters, "headline": headline,
               'pieData': pieData,
               'lineData': lineData, 'lineDates': lineDates, 'lineClusterNames': lineClusterNames
               }

    return render(request, 'general_analytics.html', context)


def details(request, cluster_id):
    headline = "Topic Analytics"
    cluster = get_object_or_404(Cluster, pk=cluster_id)
    trendingClusters = Cluster.objects.filter(ispinned=0)
    pinnedClusters = Cluster.objects.filter(ispinned=1)

    # data
    cluster_posts = {}
    posts = Post.objects.values(
        'creation_date', 'body').filter(cluster=cluster_id)
    for post in posts:
        date = int(time.mktime(post["creation_date"].timetuple())) * 1000
        if date in cluster_posts:
            cluster_posts[date]['numPosts'] += 1
        else:
            # bbcode_body = body.text_content()
            cluster_posts[date] = {"numPosts": 1, "posts": []}

        # body = html.document_fromstring(post['body']).drop_tag()
        # body = html.document_fromstring(BeautifulSoup(post['body']).getText()).text_content()
        body = BeautifulSoup(post['body']).getText()
        cluster_posts[date]['posts'].append(body)

    #Cluster word count
    wordPieData = [['Word', 'Instances']]

    words = ClusterWord.objects.filter(clusterid=cluster_id)
    for w in words:
        wordPieData.append([w.word, w.count])

    context = {'pinnedClusters': pinnedClusters, 'trendingClusters': trendingClusters, "headline": headline,
               'cluster': cluster, 'cluster_posts': cluster_posts, 'wordPieData': wordPieData}

    return render(request, 'details.html', context)


def notifications(request):
    headline = "Notifications"

    email_list = Sift.Notification.verify()
    context = {"headline": headline, 'email_list': email_list }

    if request.method == 'POST':
        if 'ADD_EMAIL' in request.POST:
            Sift.Notification.main(request.POST['ADD_EMAIL'])
        elif 'Remove' in request.POST:
            Sift.Notification.remove(request.POST.get('email'))
            return HttpResponseRedirect('/notifications')


    return render(request, 'notifications.html', context)


def clusters(request):
    headline = "Clusters"
    clusters = Cluster.objects.all();
    context = {"headline": headline, 'clusters': clusters}
    if request.method =='POST':

        print(request)

    return render(request, 'clusters.html', context)


def clustering(request):
    deleteThese = ""
    if request.method == 'POST':
        clusterForm = Sift.forms.ClusterForm(request.POST)

        if clusterForm.is_valid():
            if clusterForm.cleaned_data['cluster_type'] == 1:
                is_mini_batched = False
            else:
                is_mini_batched = True
            if clusterForm.cleaned_data['all_posts'] == 1:
                is_all_posts = True
            else:
                is_all_posts = False
            tasks.cluster_posts_with_input.delay(str(clusterForm.cleaned_data['start_date']), str(clusterForm.cleaned_data['end_date']),
                                                         int(clusterForm.cleaned_data['num_clusters']), int(clusterForm.cleaned_data['max_features']),
                                                         is_mini_batched, is_all_posts)
    if request.method == "POST" and not clusterForm.is_valid():
        stopwordDelete = StopwordDelete(request.POST)
        if stopwordDelete.is_valid():
            deleteThese = stopwordDelete.cleaned_data['word']
            for element in deleteThese:

                StopWord.objects.filter(word=element).delete()

    if request.method == "POST" and not clusterForm.is_valid() and not stopwordDelete.is_valid():
        stopwordAdd = StopwordAdd(request.POST)
        if stopwordAdd.is_valid():
            addThis = stopwordAdd.cleaned_data['add_word']
            StopWord(word=addThis).save()

    form = Sift.forms.ClusterForm()
    headline = "Clustering"

    stopwords = StopWord.objects.all().values_list("word", flat=True)
    runclustering = ClusterRun.objects.all()

    for clusterrun in runclustering:
        clusterrun.run_date = int(time.mktime(clusterrun.run_date.timetuple())) * 1000
        clusterrun.start_date = int(time.mktime(clusterrun.start_date.timetuple())) * 1000
        clusterrun.end_date = int(time.mktime(clusterrun.end_date.timetuple())) * 1000
        if clusterrun.silo_score == None:
            clusterrun.silo_score = 'null'

    context = {'headline': headline, 'form': form, 'stopwords': stopwords, 'deleteForm': StopwordDelete(), 'addForm': StopwordAdd(), 'runclustering': runclustering}
    return render(request, 'clustering.html', context)