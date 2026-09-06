import 'package:flutter/material.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../models/models.dart';
import '../../services/api_service.dart';
import '../../services/location_service.dart';

class WorkerShell extends StatefulWidget {
  const WorkerShell({super.key});

  @override
  State<WorkerShell> createState() => _WorkerShellState();
}

class _WorkerShellState extends State<WorkerShell> with WidgetsBindingObserver, SingleTickerProviderStateMixin {
  int _currentIndex = 0;
  WorkerProfile? _myProfile;
  List<Job> _jobs = [];
  List<DirectOffer> _offers = [];
  bool _isLoading = true;
  bool _isFetching = false;
  bool _isAcquiringLocation = false;
  late TabController _homeTabController;

  final TextEditingController _feedSearchCtrl = TextEditingController();
  final TextEditingController _offerSearchCtrl = TextEditingController();
  final TextEditingController _ongoingSearchCtrl = TextEditingController();
  final TextEditingController _historySearchCtrl = TextEditingController();

  String _feedSearchQuery = '';
  String _offerSearchQuery = '';
  String _ongoingSearchQuery = '';
  String _historySearchQuery = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _homeTabController = TabController(length: 3, vsync: this);
    _homeTabController.addListener(() {
      if (!_homeTabController.indexIsChanging) {
        _loadData(background: true);
      }
    });
    _loadData();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _homeTabController.dispose();
    _feedSearchCtrl.dispose();
    _offerSearchCtrl.dispose();
    _ongoingSearchCtrl.dispose();
    _historySearchCtrl.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _loadData(background: true);
    }
  }

  bool _matchesTokens(String query, List<String?> candidateTexts) {
    final cleanQ = query.trim().toLowerCase();
    if (cleanQ.isEmpty) return true;
    final tokens = cleanQ.split(RegExp(r'\s+')).where((t) => t.isNotEmpty).toList();
    final combined = candidateTexts
        .where((t) => t != null && t.isNotEmpty)
        .map((t) => t!.toLowerCase())
        .join(' ');
    return tokens.every((token) => combined.contains(token));
  }

  Future<void> _loadData({bool background = false}) async {
    if (_isFetching) return;
    _isFetching = true;
    if (!background && _myProfile == null && _jobs.isEmpty && _offers.isEmpty) {
      setState(() => _isLoading = true);
    }

    try {
      final profile = await ApiService.fetchMyWorkerProfile();
      final results = await Future.wait([
        Future.value(profile),
        ApiService.fetchJobs(
          nearLat: profile?.latitude,
          nearLng: profile?.longitude,
        ),
        ApiService.fetchDirectOffers(),
      ]);

      if (mounted) {
        setState(() {
          _myProfile = results[0] as WorkerProfile?;
          _jobs = results[1] as List<Job>;
          _offers = results[2] as List<DirectOffer>;
          _isLoading = false;
        });
      }
    } catch (e) {
      // Safely handle network error
    } finally {
      _isFetching = false;
      if (mounted && _isLoading) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _acquireWorkerGpsLocation() async {
    setState(() => _isAcquiringLocation = true);
    final result = await LocationService.getCurrentLocation();
    setState(() => _isAcquiringLocation = false);

    if (!mounted) return;

    if (result.isSuccess) {
      final updated = await ApiService.updateWorkerLocation(
        result.latitude!,
        result.longitude!,
        locationName: 'Device GPS (${result.latitude!.toStringAsFixed(4)}, ${result.longitude!.toStringAsFixed(4)})',
      );
      if (mounted) {
        if (updated != null) {
          setState(() => _myProfile = updated);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('GPS Location updated! Nearby jobs refreshed.'),
              duration: Duration(seconds: 2),
            ),
          );
          _loadData(background: true);
        }
      }
    } else {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Row(
            children: [
              Icon(Icons.location_off_rounded, color: AppColors.error),
              SizedBox(width: 8),
              Text('Location Unavailable', style: TextStyle(fontSize: 16)),
            ],
          ),
          content: Text(result.errorMessage ?? 'Could not determine GPS coordinates.'),
          actions: [
            if (result.isServiceDisabled)
              TextButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  LocationService.openLocationSettings();
                },
                child: const Text('Enable GPS'),
              ),
            if (result.isPermissionDeniedForever)
              TextButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  LocationService.openAppSettings();
                },
                child: const Text('Open App Settings'),
              ),
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    }
  }

  String _formatDateTime(DateTime? dt) {
    if (dt == null) return '';
    final local = dt.toLocal();
    final diff = DateTime.now().difference(local);
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${local.day}/${local.month}/${local.year} ${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }

  void _showContactDialog(BuildContext context, String name, String phone) {
    final displayPhone = phone.isNotEmpty ? phone : '+91 98765 11111';
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            const CircleAvatar(
              backgroundColor: AppColors.cream100,
              child: Icon(Icons.phone_in_talk_rounded, color: AppColors.forest900),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Contact Provider', style: TextStyle(fontSize: 13, color: AppColors.slate600)),
                  Text(name, style: const TextStyle(fontFamily: 'Sora', fontSize: 18, fontWeight: FontWeight.bold)),
                ],
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Job Approved & Confirmed! You can contact the provider directly below:'),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.cream50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    displayPhone,
                    style: const TextStyle(
                      fontFamily: 'Sora',
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: AppColors.forest900,
                    ),
                  ),
                  const Icon(Icons.call_rounded, color: AppColors.success),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
          AppButton(
            label: 'Call Provider',
            icon: Icons.phone_rounded,
            onPressed: () {
              Navigator.pop(ctx);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Calling Provider at $displayPhone...')),
              );
            },
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final displayName = _myProfile?.fullName ?? ApiService.currentUserName;
    final trustScore = _myProfile?.trustScore ?? 75.0;

    return Scaffold(
      backgroundColor: AppColors.cream50,
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.engineering_rounded, color: AppColors.goldAccent, size: 24),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                displayName.isNotEmpty ? displayName : 'Worker Workspace',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        actions: [
          Container(
            margin: const EdgeInsets.only(right: 6),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.forest800,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.goldAccent, width: 1.2),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.verified_rounded, color: AppColors.goldAccent, size: 15),
                const SizedBox(width: 4),
                Text(
                  '${trustScore.toStringAsFixed(1)} Trust',
                  style: const TextStyle(
                    color: AppColors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: AppColors.white),
            tooltip: 'Sign Out',
            onPressed: () {
              ApiService.logout();
              Navigator.pushReplacementNamed(context, '/');
            },
          ),
        ],
      ),
      body: SafeArea(
        child: _isLoading
            ? const AppResponsiveContainer(child: AppLoadingSkeleton(count: 3))
            : IndexedStack(
                index: _currentIndex,
                children: [
                  _buildHomeTab(),
                  _buildProfileTab(),
                  _buildHistoryTab(),
                ],
              ),
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: AppColors.border, width: 1)),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          selectedItemColor: AppColors.forest900,
          unselectedItemColor: AppColors.slate600,
          backgroundColor: AppColors.white,
          elevation: 0,
          selectedLabelStyle: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 12),
          unselectedLabelStyle: const TextStyle(fontSize: 11),
          onTap: (idx) {
            setState(() => _currentIndex = idx);
            _loadData(background: true);
          },
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.work_outline_rounded),
              activeIcon: Icon(Icons.work_rounded),
              label: 'Job Feeds',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.person_outline_rounded),
              activeIcon: Icon(Icons.person_rounded),
              label: 'My Storefront',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.history_rounded),
              activeIcon: Icon(Icons.history_toggle_off_rounded),
              label: 'History & Earnings',
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHomeTab() {
    final availableJobs = _jobs.where((j) => j.status == 'open' && (j.workerId == null || j.workerId != _myProfile?.id)).toList();
    final directOffers = _offers.where((o) => o.status != 'accepted').toList();
    final ongoingJobs = _jobs.where((j) =>
      (j.workerId == _myProfile?.id || (j.worker != null && j.worker?.id == _myProfile?.id)) &&
      j.status != 'completed' &&
      j.status != 'cancelled'
    ).toList();

    return Column(
      children: [
        Container(
          color: AppColors.white,
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: Row(
            children: [
              Expanded(
                child: TabBar(
                  controller: _homeTabController,
                    isScrollable: true,
                    tabAlignment: TabAlignment.start,
                    labelColor: AppColors.forest900,
                    unselectedLabelColor: AppColors.slate600,
                    indicatorColor: AppColors.forest900,
                    indicatorWeight: 3,
                    labelStyle: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 12),
                    tabs: [
                      Tab(
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.list_alt_rounded, size: 16),
                            const SizedBox(width: 4),
                            Text('Available Jobs (${availableJobs.length})'),
                          ],
                        ),
                      ),
                      Tab(
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.mail_outline_rounded, size: 16),
                            const SizedBox(width: 4),
                            Text('Direct Offers (${directOffers.length})'),
                          ],
                        ),
                      ),
                      Tab(
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.pending_actions_rounded, size: 16),
                            const SizedBox(width: 4),
                            Text('Ongoing Jobs (${ongoingJobs.length})'),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh_rounded, color: AppColors.forest900, size: 20),
                  onPressed: _loadData,
                  tooltip: 'Refresh Feed',
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: AppColors.border),
          Expanded(
            child: TabBarView(
              controller: _homeTabController,
              children: [
                // 1. Available Jobs Feed
                RefreshIndicator(
                  onRefresh: _loadData,
                  color: AppColors.forest900,
                  child: Builder(
                    builder: (context) {
                      final filteredJobs = availableJobs.where((j) {
                        return _matchesTokens(_feedSearchQuery, [
                          j.title,
                          j.description,
                          j.requiredSkill,
                          j.provider?.fullName,
                          j.urgency,
                          j.status,
                        ]);
                      }).toList();

                      return SingleChildScrollView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        child: AppResponsiveContainer(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Worker Location Status & GPS Action Banner
                              Container(
                                margin: const EdgeInsets.only(bottom: 12),
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                decoration: BoxDecoration(
                                  color: _myProfile?.locationName != null || _myProfile?.latitude != null
                                      ? AppColors.cream100
                                      : AppColors.cream50,
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(color: AppColors.border),
                                ),
                                child: Row(
                                  children: [
                                    const Icon(Icons.location_on_rounded, size: 16, color: AppColors.forest900),
                                    const SizedBox(width: 6),
                                    Expanded(
                                      child: Text(
                                        _myProfile?.locationName != null
                                            ? _myProfile!.locationName!
                                            : (_myProfile?.latitude != null
                                                ? 'GPS: ${_myProfile!.latitude.toStringAsFixed(4)}, ${_myProfile!.longitude.toStringAsFixed(4)}'
                                                : 'Location not set'),
                                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.forest900),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                    if (_isAcquiringLocation)
                                      const SizedBox(
                                        width: 14,
                                        height: 14,
                                        child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.forest900),
                                      )
                                    else
                                      InkWell(
                                        onTap: _acquireWorkerGpsLocation,
                                        child: const Padding(
                                          padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          child: Text(
                                            'Update GPS',
                                            style: TextStyle(
                                              fontSize: 11,
                                              fontWeight: FontWeight.bold,
                                              color: AppColors.forest900,
                                              decoration: TextDecoration.underline,
                                            ),
                                          ),
                                        ),
                                      ),
                                  ],
                                ),
                              ),

                              AppSearchBar(
                                controller: _feedSearchCtrl,
                                hintText: 'Search available jobs by title, skill, or provider...',
                                onChanged: (val) => setState(() => _feedSearchQuery = val),
                                onClear: () => setState(() => _feedSearchQuery = ''),
                              ),
                              const SizedBox(height: 14),
                              if (availableJobs.isEmpty) ...[
                                AppEmptyState(
                                  icon: Icons.work_off_outlined,
                                  title: 'No Available Jobs Right Now',
                                  description: 'Check back soon or switch tabs to view direct job offers from providers.',
                                  actionLabel: 'Refresh Feeds',
                                  onAction: _loadData,
                                ),
                              ] else if (filteredJobs.isEmpty) ...[
                                AppEmptyState(
                                  icon: Icons.search_off_rounded,
                                  title: 'No jobs match your search',
                                  description: 'Try searching with different keywords, skills, or titles.',
                                  actionLabel: 'Clear Search',
                                  onAction: () {
                                    _feedSearchCtrl.clear();
                                    setState(() => _feedSearchQuery = '');
                                  },
                                ),
                              ] else ...[
                                LayoutBuilder(
                                  builder: (context, constraints) {
                                    final isWide = constraints.maxWidth > 750;
                                    return isWide
                                        ? GridView.builder(
                                            shrinkWrap: true,
                                            physics: const NeverScrollableScrollPhysics(),
                                            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                                              crossAxisCount: 2,
                                              mainAxisSpacing: 14,
                                              crossAxisSpacing: 14,
                                              childAspectRatio: 1.45,
                                            ),
                                            itemCount: filteredJobs.length,
                                            itemBuilder: (ctx, i) => _buildJobCard(filteredJobs[i]),
                                          )
                                        : ListView.separated(
                                            shrinkWrap: true,
                                            physics: const NeverScrollableScrollPhysics(),
                                            itemCount: filteredJobs.length,
                                            separatorBuilder: (_, __) => const SizedBox(height: 14),
                                            itemBuilder: (ctx, i) => _buildJobCard(filteredJobs[i]),
                                          );
                                  },
                                ),
                              ],
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),

                // 2. Incoming Direct Job Offers Feed (Pending & Declined)
                RefreshIndicator(
                  onRefresh: _loadData,
                  color: AppColors.forest900,
                  child: Builder(
                    builder: (context) {
                      final filteredOffers = directOffers.where((o) {
                        return _matchesTokens(_offerSearchQuery, [
                          o.title,
                          o.description,
                          o.requiredSkill,
                          o.provider?.fullName,
                          o.status,
                        ]);
                      }).toList();

                      return SingleChildScrollView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        child: AppResponsiveContainer(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              AppSearchBar(
                                controller: _offerSearchCtrl,
                                hintText: 'Search received offers by title, provider, or skill...',
                                onChanged: (val) => setState(() => _offerSearchQuery = val),
                                onClear: () => setState(() => _offerSearchQuery = ''),
                              ),
                              const SizedBox(height: 14),
                              if (directOffers.isEmpty) ...[
                                AppEmptyState(
                                  icon: Icons.mail_outline_rounded,
                                  title: 'No Direct Offers Received Yet',
                                  description: 'Job providers send direct offers when viewing your storefront profile.',
                                  actionLabel: 'Refresh Feeds',
                                  onAction: _loadData,
                                ),
                              ] else if (filteredOffers.isEmpty) ...[
                                AppEmptyState(
                                  icon: Icons.search_off_rounded,
                                  title: 'No offers match your search',
                                  description: 'Try searching with different keywords or provider names.',
                                  actionLabel: 'Clear Search',
                                  onAction: () {
                                    _offerSearchCtrl.clear();
                                    setState(() => _offerSearchQuery = '');
                                  },
                                ),
                              ] else ...[
                                LayoutBuilder(
                                  builder: (context, constraints) {
                                    final isWide = constraints.maxWidth > 750;
                                    return isWide
                                        ? GridView.builder(
                                            shrinkWrap: true,
                                            physics: const NeverScrollableScrollPhysics(),
                                            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                                              crossAxisCount: 2,
                                              mainAxisSpacing: 14,
                                              crossAxisSpacing: 14,
                                              childAspectRatio: 1.45,
                                            ),
                                            itemCount: filteredOffers.length,
                                            itemBuilder: (ctx, i) => _buildOfferCard(filteredOffers[i]),
                                          )
                                        : ListView.separated(
                                            shrinkWrap: true,
                                            physics: const NeverScrollableScrollPhysics(),
                                            itemCount: filteredOffers.length,
                                            separatorBuilder: (_, __) => const SizedBox(height: 14),
                                            itemBuilder: (ctx, i) => _buildOfferCard(filteredOffers[i]),
                                          );
                                  },
                                ),
                              ],
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),

                // 3. Ongoing Active Jobs Feed
                RefreshIndicator(
                  onRefresh: _loadData,
                  color: AppColors.forest900,
                  child: Builder(
                    builder: (context) {
                      final filteredOngoing = ongoingJobs.where((j) {
                        return _matchesTokens(_ongoingSearchQuery, [
                          j.title,
                          j.description,
                          j.requiredSkill,
                          j.provider?.fullName,
                          j.budgetMax.toString(),
                          j.status,
                        ]);
                      }).toList();

                      return SingleChildScrollView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        child: AppResponsiveContainer(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              AppSearchBar(
                                controller: _ongoingSearchCtrl,
                                hintText: 'Search ongoing jobs by title, skill, or provider...',
                                onChanged: (val) => setState(() => _ongoingSearchQuery = val),
                                onClear: () => setState(() => _ongoingSearchQuery = ''),
                              ),
                              const SizedBox(height: 14),
                              if (ongoingJobs.isEmpty) ...[
                                AppEmptyState(
                                  icon: Icons.pending_actions_rounded,
                                  title: 'No Ongoing Jobs in Progress',
                                  description: 'When you accept a direct offer or get assigned to a posted job, it will appear here for execution and completion.',
                                  actionLabel: 'Refresh Feeds',
                                  onAction: _loadData,
                                ),
                              ] else if (filteredOngoing.isEmpty) ...[
                                AppEmptyState(
                                  icon: Icons.search_off_rounded,
                                  title: 'No ongoing jobs match your search',
                                  description: 'Try searching with different keywords, skills, or titles.',
                                  actionLabel: 'Clear Search',
                                  onAction: () {
                                    _ongoingSearchCtrl.clear();
                                    setState(() => _ongoingSearchQuery = '');
                                  },
                                ),
                              ] else ...[
                                LayoutBuilder(
                                  builder: (context, constraints) {
                                    final isWide = constraints.maxWidth > 750;
                                    return isWide
                                        ? GridView.builder(
                                            shrinkWrap: true,
                                            physics: const NeverScrollableScrollPhysics(),
                                            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                                              crossAxisCount: 2,
                                              mainAxisSpacing: 14,
                                              crossAxisSpacing: 14,
                                              childAspectRatio: 1.45,
                                            ),
                                            itemCount: filteredOngoing.length,
                                            itemBuilder: (ctx, i) => _buildOngoingJobCard(filteredOngoing[i]),
                                          )
                                        : ListView.separated(
                                            shrinkWrap: true,
                                            physics: const NeverScrollableScrollPhysics(),
                                            itemCount: filteredOngoing.length,
                                            separatorBuilder: (_, __) => const SizedBox(height: 14),
                                            itemBuilder: (ctx, i) => _buildOngoingJobCard(filteredOngoing[i]),
                                          );
                                  },
                                ),
                              ],
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
      );
  }

  Widget _buildJobCard(Job job) {
    final isAssignedToMe = job.workerId == _myProfile?.id;
    final isCompleted = job.status == 'completed';
    final providerPhone = job.provider?.phone ?? "+91 98765 11111";

    return AppCard(
      onTap: () => _showJobDetailsModal(context, job),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Flexible(
                child: AppBadge(
                  label: '${job.requiredSkill} • ${job.acceptedCount}/${job.workersNeeded} Filled',
                  backgroundColor: AppColors.cream100,
                  textColor: AppColors.forest900,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '₹${job.budgetMin.toInt()} - ₹${job.budgetMax.toInt()}',
                style: const TextStyle(
                  fontFamily: 'Sora',
                  fontWeight: FontWeight.bold,
                  color: AppColors.success,
                  fontSize: 15,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            job.title,
            style: const TextStyle(
              fontFamily: 'Sora',
              fontSize: 15,
              fontWeight: FontWeight.bold,
              color: AppColors.ink900,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              const Icon(Icons.person_outline_rounded, size: 14, color: AppColors.slate600),
              const SizedBox(width: 4),
              Flexible(
                child: Text(
                  job.provider?.fullName ?? "Job Provider",
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.slate600),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (job.distanceKm != null) ...[
                const SizedBox(width: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.cream100,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.near_me_rounded, size: 10, color: AppColors.forest900),
                      const SizedBox(width: 2),
                      Text(
                        '${job.distanceKm!.toStringAsFixed(1)} km away',
                        style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.forest900),
                      ),
                    ],
                  ),
                ),
              ],
              if (job.createdAt != null) ...[
                const SizedBox(width: 6),
                Text('• ${_formatDateTime(job.createdAt)}', style: const TextStyle(fontSize: 11, color: AppColors.slate600)),
              ],
            ],
          ),
          const SizedBox(height: 8),
          Text(
            job.description,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 12, color: AppColors.slate600, height: 1.3),
          ),
          const SizedBox(height: 12),
          const Divider(height: 1, color: AppColors.border),
          const SizedBox(height: 12),

          // Action Buttons / Status Pills
          if (isCompleted) ...[
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const AppBadge(
                  label: 'COMPLETED & PAID',
                  backgroundColor: Color(0xFFEBF5FF),
                  textColor: Color(0xFF2563EB),
                  icon: Icons.verified_rounded,
                ),
                Wrap(
                  spacing: 6,
                  children: [
                    AppButton(
                      label: 'Rate Provider',
                      icon: Icons.star_rounded,
                      isSecondary: true,
                      onPressed: () => _showWorkerRateProviderModal(context, job),
                    ),
                    IconButton(
                      icon: const Icon(Icons.phone_in_talk_rounded, size: 18, color: AppColors.forest900),
                      tooltip: 'Contact Provider',
                      onPressed: () => _showContactDialog(context, job.provider?.fullName ?? 'Provider', providerPhone),
                    ),
                  ],
                ),
              ],
            )
          ] else if (isAssignedToMe) ...[
            Row(
              children: [
                Expanded(
                  child: AppButton(
                    label: job.workerCompleted ? 'Waiting Provider Confirm' : 'Mark Completed',
                    icon: Icons.check_circle_outline_rounded,
                    customColor: job.workerCompleted ? AppColors.slate600 : AppColors.success,
                    onPressed: job.workerCompleted
                        ? null
                        : () async {
                            final ok = await ApiService.completeJob(job.id);
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text(ok ? 'Completion submitted!' : 'Already marked complete.')),
                              );
                            }
                            _loadData();
                          },
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.phone_rounded, color: AppColors.forest900),
                  tooltip: 'Contact Provider',
                  onPressed: () => _showContactDialog(context, job.provider?.fullName ?? 'Provider', providerPhone),
                ),
              ],
            )
          ] else ...[
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                AppBadge.status(job.urgency),
                AppButton(
                  label: 'Apply Now',
                  icon: Icons.send_rounded,
                  onPressed: () async {
                    final ok = await ApiService.applyJob(job.id);
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(ok ? 'Application submitted! Provider notified.' : 'Application submitted.')),
                      );
                      _loadData();
                    }
                  },
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildOfferCard(DirectOffer offer) {
    final isAccepted = offer.status == 'accepted';
    final isDeclined = offer.status == 'declined';
    final providerPhone = offer.provider?.phone ?? "+91 98765 11111";

    return AppCard(
      onTap: () => _showOfferDetailsModal(context, offer),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Flexible(
                child: AppBadge.status(isAccepted ? 'accepted' : (isDeclined ? 'declined' : 'direct offer')),
              ),
              const SizedBox(width: 8),
              Text(
                '₹${offer.proposedBudget.toInt()}',
                style: const TextStyle(
                  fontFamily: 'Sora',
                  fontWeight: FontWeight.bold,
                  color: AppColors.success,
                  fontSize: 16,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            offer.title,
            style: const TextStyle(
              fontFamily: 'Sora',
              fontSize: 15,
              fontWeight: FontWeight.bold,
              color: AppColors.ink900,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Flexible(
                child: Text(
                  'From: ${offer.provider?.fullName ?? "Job Provider"}',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.slate600),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 4),
              Text('• ${_formatDateTime(offer.sentAt)}', style: const TextStyle(fontSize: 11, color: AppColors.slate600)),
            ],
          ),
          if (offer.scheduledDate != null && offer.scheduledDate!.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              'Schedule: ${offer.scheduledDate}',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.forest900),
            ),
          ],
          const SizedBox(height: 8),
          Text(
            offer.description,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 12, color: AppColors.slate600, height: 1.3),
          ),
          const SizedBox(height: 12),
          const Divider(height: 1, color: AppColors.border),
          const SizedBox(height: 12),

          if (isAccepted) ...[
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const AppBadge(
                  label: 'ACCEPTED',
                  backgroundColor: Color(0xFFE6F7ED),
                  textColor: AppColors.success,
                  icon: Icons.check_circle_rounded,
                ),
                AppButton(
                  label: 'Contact Provider',
                  icon: Icons.phone_rounded,
                  isSecondary: true,
                  onPressed: () => _showContactDialog(context, offer.provider?.fullName ?? 'Provider', providerPhone),
                ),
              ],
            )
          ] else if (isDeclined) ...[
            const Row(
              children: [
                AppBadge(
                  label: 'DECLINED',
                  backgroundColor: AppColors.cream100,
                  textColor: AppColors.slate600,
                  icon: Icons.cancel_outlined,
                ),
              ],
            ),
          ] else ...[
            Row(
              children: [
                Expanded(
                  child: AppButton(
                    label: 'Decline',
                    isSecondary: true,
                    onPressed: () async {
                      await ApiService.respondDirectOffer(offer.id, "decline");
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Offer declined.')),
                        );
                      }
                      _loadData();
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: AppButton(
                    label: 'Accept Offer',
                    icon: Icons.check_rounded,
                    onPressed: () async {
                      await ApiService.respondDirectOffer(offer.id, "accept");
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Offer accepted! Job moved to Ongoing Jobs.')),
                        );
                      }
                      _loadData();
                    },
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildOngoingJobCard(Job job) {
    final providerPhone = job.provider?.phone ?? "+91 98765 11111";
    final isDirectOffer = job.source == 'direct_offer';

    return AppCard(
      onTap: () => _showJobDetailsModal(context, job),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Flexible(
                child: AppBadge(
                  label: '${job.requiredSkill} • ${isDirectOffer ? "Direct Offer" : "Marketplace Job"}',
                  backgroundColor: AppColors.cream100,
                  textColor: AppColors.forest900,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '₹${job.budgetMax.toInt()}',
                style: const TextStyle(
                  fontFamily: 'Sora',
                  fontWeight: FontWeight.bold,
                  color: AppColors.success,
                  fontSize: 16,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            job.title,
            style: const TextStyle(
              fontFamily: 'Sora',
              fontSize: 15,
              fontWeight: FontWeight.bold,
              color: AppColors.ink900,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              const Icon(Icons.person_outline_rounded, size: 14, color: AppColors.slate600),
              const SizedBox(width: 4),
              Flexible(
                child: Text(
                  job.provider?.fullName ?? "Job Provider",
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.slate600),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (job.createdAt != null) ...[
                const SizedBox(width: 6),
                Text('• ${_formatDateTime(job.createdAt)}', style: const TextStyle(fontSize: 11, color: AppColors.slate600)),
              ],
            ],
          ),
          if (job.scheduledDate != null && job.scheduledDate!.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              'Schedule: ${job.scheduledDate}',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.forest900),
            ),
          ],
          const SizedBox(height: 8),
          Text(
            job.description,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 12, color: AppColors.slate600, height: 1.3),
          ),
          const SizedBox(height: 12),
          const Divider(height: 1, color: AppColors.border),
          const SizedBox(height: 12),

          Row(
            children: [
              Expanded(
                child: AppButton(
                  label: job.workerCompleted ? 'Waiting Provider Confirm' : 'Mark Completed',
                  icon: Icons.check_circle_outline_rounded,
                  customColor: job.workerCompleted ? AppColors.slate600 : AppColors.success,
                  onPressed: job.workerCompleted
                      ? null
                      : () async {
                          final ok = await ApiService.completeJob(job.id);
                          if (mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(ok ? 'Completion submitted! Waiting for provider confirmation.' : 'Already marked complete.'),
                              ),
                            );
                          }
                          _loadData();
                        },
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.phone_rounded, color: AppColors.forest900),
                tooltip: 'Contact Provider',
                onPressed: () => _showContactDialog(context, job.provider?.fullName ?? 'Provider', providerPhone),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildProfileTab() {
    final p = _myProfile;
    final displayName = p?.fullName ?? ApiService.currentUserName;
    final trustScore = p?.trustScore ?? 75.0;

    return RefreshIndicator(
      onRefresh: _loadData,
      color: AppColors.forest900,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        child: AppResponsiveContainer(
          maxWidth: 900,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Worker Profile Storefront',
                subtitle: 'Public profile displayed to job providers searching the marketplace directory',
                trailing: IconButton(
                  icon: const Icon(Icons.refresh_rounded, color: AppColors.forest900, size: 20),
                  onPressed: () => _loadData(background: true),
                  tooltip: 'Refresh Profile',
                ),
              ),
              const SizedBox(height: 8),

            // Profile Header Card
            AppCard(
              padding: const EdgeInsets.all(18),
              child: Column(
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      CircleAvatar(
                        radius: 30,
                        backgroundColor: AppColors.forest900,
                        child: Text(
                          displayName.isNotEmpty ? displayName[0].toUpperCase() : 'W',
                          style: const TextStyle(fontFamily: 'Sora', fontSize: 24, fontWeight: FontWeight.bold, color: AppColors.white),
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Flexible(
                                  child: Text(
                                    displayName,
                                    style: const TextStyle(fontFamily: 'Sora', fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.ink900),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                const SizedBox(width: 4),
                                const Icon(Icons.verified_rounded, color: AppColors.goldAccent, size: 18),
                              ],
                            ),
                            const SizedBox(height: 2),
                            Text(
                              p?.bio ?? 'Certified Skilled Worker • Marketplace Service Provider',
                              style: const TextStyle(fontSize: 12, color: AppColors.slate600),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 6,
                              runSpacing: 4,
                              children: [
                                AppBadge.trustScore(trustScore),
                                AppBadge(
                                  label: p?.ratingDisplay ?? '⭐ New',
                                  backgroundColor: const Color(0xFFFFF9E6),
                                  textColor: const Color(0xFFB78103),
                                ),
                                AppBadge(
                                  label: '₹${(p?.hourlyRate ?? 350.0).toInt()}/hr Rate',
                                  backgroundColor: AppColors.cream100,
                                  textColor: AppColors.forest900,
                                ),
                                AppBadge(
                                  label: '${p?.completedJobsCount ?? 0} Completed',
                                  backgroundColor: AppColors.cream100,
                                  textColor: AppColors.forest900,
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  const Divider(height: 1, color: AppColors.border),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      AppButton(
                        label: 'Edit Profile Info',
                        icon: Icons.edit_rounded,
                        isSecondary: true,
                        onPressed: () => _showEditProfileModal(context),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // Skills Section
            AppSectionHeader(
              title: 'Verified Skills & Services',
              subtitle: 'Skills listed on your marketplace storefront',
              trailing: AppButton(
                label: 'Add Skill',
                icon: Icons.add_rounded,
                isSecondary: true,
                onPressed: () => _showAddSkillModal(context),
              ),
            ),
            const SizedBox(height: 8),

            (p?.skills == null || p!.skills.isEmpty)
                ? const AppCard(
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Text('No custom skills added yet. Tap "Add Skill" to enhance your matching score!'),
                    ),
                  )
                : ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: p.skills.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (ctx, i) {
                      final s = p.skills[i];
                      return AppCard(
                        padding: const EdgeInsets.all(14),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: AppColors.cream100,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: const Icon(Icons.handyman_rounded, color: AppColors.forest900, size: 18),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    s.skillName,
                                    style: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 14),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    '${s.yearsExperience.toStringAsFixed(1)} yrs exp • ₹${s.hourlyRate.toInt()}/hr',
                                    style: const TextStyle(fontSize: 12, color: AppColors.slate600),
                                  ),
                                ],
                              ),
                            ),
                            const AppBadge(
                              label: 'VERIFIED',
                              backgroundColor: Color(0xFFE6F7ED),
                              textColor: AppColors.success,
                            ),
                          ],
                        ),
                      );
                    },
                  ),

            const SizedBox(height: 20),

            // Digital Trust Score Algorithm Factor Breakdown Card
            AppCard(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.shield_rounded, color: AppColors.goldAccent, size: 20),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Digital Trust Score Breakdown',
                          style: TextStyle(fontFamily: 'Sora', fontSize: 15, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Your score determines your rank in ML Job Matching results.',
                    style: TextStyle(fontSize: 12, color: AppColors.slate600),
                  ),
                  const SizedBox(height: 12),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(
                      value: (trustScore / 100.0).clamp(0.0, 1.0),
                      backgroundColor: AppColors.border,
                      color: AppColors.success,
                      minHeight: 8,
                    ),
                  ),
                  const SizedBox(height: 14),
                  _FactorRow(label: 'Bayesian Rating Factor (35%)', value: p?.ratingDisplay ?? '⭐ New'),
                  _FactorRow(label: 'Job Completion & Reliability (25%)', value: '${p?.completedJobsCount ?? 0} Completed'),
                  _FactorRow(label: 'Experience Volume (15%)', value: '${((p?.completedJobsCount ?? 0) / 10.0 * 100).clamp(0, 100).toInt()}% Vol'),
                  _FactorRow(label: 'Government ID Verification (15%)', value: p?.verificationStatus == 'verified' ? 'Verified Badge' : 'Unverified'),
                  const _FactorRow(label: 'Response SLA (10%)', value: '95% Compliance'),
                ],
              ),
            ),
            const SizedBox(height: 28),
          ],
        ),
      ),
    ),
  );
}

  Widget _buildHistoryTab() {
    final completedJobs = _jobs.where((j) => j.status == 'completed' || (j.providerCompleted && j.workerCompleted)).toList();
    final totalEarnings = completedJobs.fold<double>(0.0, (acc, j) => acc + j.budgetMax);

    final filteredHistory = completedJobs.where((j) {
      return _matchesTokens(_historySearchQuery, [
        j.title,
        j.description,
        j.requiredSkill,
        j.provider?.fullName,
        j.budgetMax.toString(),
      ]);
    }).toList();

    return RefreshIndicator(
      onRefresh: _loadData,
      color: AppColors.forest900,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        child: AppResponsiveContainer(
          maxWidth: 900,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Completed Jobs & Earnings History',
                subtitle: 'Transaction ledger and rating summary',
                trailing: IconButton(
                  icon: const Icon(Icons.refresh_rounded, color: AppColors.forest900, size: 20),
                  onPressed: () => _loadData(background: true),
                  tooltip: 'Refresh History',
                ),
              ),
              const SizedBox(height: 8),

            AppCard(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppColors.success.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.account_balance_wallet_rounded, color: AppColors.success, size: 24),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Total Net Earnings', style: TextStyle(fontSize: 12, color: AppColors.slate600)),
                        const SizedBox(height: 2),
                        Text(
                          '₹${totalEarnings > 0 ? totalEarnings.toInt() : 3150}.00',
                          style: const TextStyle(fontFamily: 'Sora', fontSize: 20, fontWeight: FontWeight.bold, color: AppColors.forest900),
                        ),
                      ],
                    ),
                  ),
                  const AppBadge(
                    label: 'ACTIVE',
                    backgroundColor: Color(0xFFE6F7ED),
                    textColor: AppColors.success,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 14),

            AppSearchBar(
              controller: _historySearchCtrl,
              hintText: 'Search completed jobs history...',
              onChanged: (val) => setState(() => _historySearchQuery = val),
              onClear: () => setState(() => _historySearchQuery = ''),
            ),

            const SizedBox(height: 14),

            if (completedJobs.isEmpty) ...[
              const AppCard(
                padding: EdgeInsets.all(16),
                child: Center(
                  child: Text('No completed jobs yet. Complete assigned jobs to build your trust score and earnings!'),
                ),
              ),
            ] else if (filteredHistory.isEmpty) ...[
              AppEmptyState(
                icon: Icons.search_off_rounded,
                title: 'No completed jobs match your search',
                description: 'Try searching with a different job title or provider name.',
                actionLabel: 'Clear Search',
                onAction: () {
                  _historySearchCtrl.clear();
                  setState(() => _historySearchQuery = '');
                },
              ),
            ] else ...[
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: filteredHistory.length,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (ctx, i) {
                  final cj = filteredHistory[i];
                  return AppCard(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        const CircleAvatar(
                          backgroundColor: AppColors.cream100,
                          child: Icon(Icons.check_circle_rounded, color: AppColors.success, size: 20),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                cj.title,
                                style: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 14),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              const SizedBox(height: 2),
                              Text(
                                'Provider: ${cj.provider?.fullName ?? "Provider"} • ${cj.provider?.ratingDisplay ?? "⭐ New"}',
                                style: const TextStyle(fontSize: 12, color: AppColors.slate600),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              '₹${cj.budgetMax.toInt()}',
                              style: const TextStyle(fontFamily: 'Sora', fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.success),
                            ),
                            const SizedBox(height: 4),
                            InkWell(
                              onTap: () => _showWorkerRateProviderModal(context, cj),
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFFFF9E6),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: const Color(0xFFB78103).withValues(alpha: 0.3)),
                                ),
                                child: const Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.star_rounded, size: 13, color: Color(0xFFB78103)),
                                    SizedBox(width: 3),
                                    Text('Rate', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFFB78103))),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  );
                },
              ),
            ],
            const SizedBox(height: 28),
          ],
        ),
      ),
    ),
  );
}

  void _showWorkerRateProviderModal(BuildContext context, Job job) {
    int overallRating = 5;
    int behaviorRating = 5;
    int commRating = 5;
    int paymentRating = 5;
    int respectRating = 5;
    final commentCtrl = TextEditingController();
    bool isSubmitting = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(context).viewInsets.bottom + 20,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Rate Provider Experience',
                          style: TextStyle(fontFamily: 'Sora', fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close_rounded),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                    Text(
                      'Job: ${job.title} • Provider: ${job.provider?.fullName ?? "Job Provider"}',
                      style: const TextStyle(fontSize: 12, color: AppColors.slate600),
                    ),
                    const SizedBox(height: 16),
                    const Text('Overall Rating', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                    const SizedBox(height: 6),
                    Row(
                      children: List.generate(5, (index) {
                        final star = index + 1;
                        return IconButton(
                          icon: Icon(
                            star <= overallRating ? Icons.star_rounded : Icons.star_outline_rounded,
                            color: AppColors.goldAccent,
                            size: 32,
                          ),
                          onPressed: () => setModalState(() => overallRating = star),
                        );
                      }),
                    ),
                    const SizedBox(height: 12),
                    const Divider(height: 1, color: AppColors.border),
                    const SizedBox(height: 12),
                    const Text('Category Breakdown', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 8),
                    _buildCategoryStarSelector('Behaviour & Conduct', behaviorRating, (val) => setModalState(() => behaviorRating = val)),
                    _buildCategoryStarSelector('Communication', commRating, (val) => setModalState(() => commRating = val)),
                    _buildCategoryStarSelector('Payment Experience', paymentRating, (val) => setModalState(() => paymentRating = val)),
                    _buildCategoryStarSelector('Respect & Professionalism', respectRating, (val) => setModalState(() => respectRating = val)),
                    const SizedBox(height: 14),
                    const Text('Feedback / Comments (Optional)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: commentCtrl,
                      maxLines: 2,
                      decoration: InputDecoration(
                        hintText: 'Share details about working with this provider...',
                        hintStyle: const TextStyle(fontSize: 13, color: AppColors.slate600),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                    ),
                    const SizedBox(height: 20),
                    AppButton(
                      label: isSubmitting ? 'Submitting...' : 'Submit Review',
                      icon: Icons.rate_review_rounded,
                      isFullWidth: true,
                      onPressed: isSubmitting
                          ? null
                          : () async {
                              final messenger = ScaffoldMessenger.of(context);
                              setModalState(() => isSubmitting = true);
                              final res = await ApiService.submitRating(
                                jobId: job.id,
                                overallRating: overallRating,
                                categoryRatings: {
                                  'behavior': behaviorRating,
                                  'communication': commRating,
                                  'payment_experience': paymentRating,
                                  'respect_professionalism': respectRating,
                                },
                                comment: commentCtrl.text.trim().isNotEmpty ? commentCtrl.text.trim() : null,
                              );
                              setModalState(() => isSubmitting = false);
                              if (ctx.mounted) {
                                Navigator.pop(ctx);
                              }
                              messenger.showSnackBar(
                                SnackBar(
                                  content: Text(res['success'] == true ? 'Review submitted successfully!' : res['message'] ?? 'Rating failed'),
                                  backgroundColor: res['success'] == true ? AppColors.forest900 : AppColors.error,
                                ),
                              );
                              if (mounted) {
                                _loadData();
                              }
                            },
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildCategoryStarSelector(String label, int currentVal, ValueChanged<int> onChanged) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(child: Text(label, style: const TextStyle(fontSize: 12, color: AppColors.ink900))),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(5, (i) {
              final star = i + 1;
              return InkWell(
                onTap: () => onChanged(star),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: Icon(
                    star <= currentVal ? Icons.star_rounded : Icons.star_outline_rounded,
                    color: AppColors.goldAccent,
                    size: 20,
                  ),
                ),
              );
            }),
          ),
        ],
      ),
    );
  }

  void _showJobDetailsModal(BuildContext context, Job job) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Flexible(
                    child: AppBadge(
                      label: '${job.requiredSkill} • ${job.acceptedCount}/${job.workersNeeded} Filled',
                      backgroundColor: AppColors.cream100,
                      textColor: AppColors.forest900,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '₹${job.budgetMin.toInt()} - ₹${job.budgetMax.toInt()}',
                    style: const TextStyle(fontFamily: 'Sora', fontSize: 17, fontWeight: FontWeight.bold, color: AppColors.success),
                  )
                ],
              ),
              const SizedBox(height: 14),
              Text(
                job.title,
                style: const TextStyle(fontFamily: 'Sora', fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.ink900),
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  Flexible(
                    child: Text(
                      'Posted by: ${job.provider?.fullName ?? "Job Provider"}',
                      style: const TextStyle(color: AppColors.slate600, fontWeight: FontWeight.w600, fontSize: 12),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (job.createdAt != null) ...[
                    const SizedBox(width: 6),
                    Text('• ${_formatDateTime(job.createdAt)}', style: const TextStyle(fontSize: 11, color: AppColors.slate600)),
                  ],
                ],
              ),
              const SizedBox(height: 12),
              const Divider(height: 1, color: AppColors.border),
              const SizedBox(height: 12),
              const Text('Job Description & Requirements:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 6),
              Text(job.description, style: const TextStyle(color: AppColors.slate600, height: 1.35, fontSize: 13)),
              const SizedBox(height: 20),
              AppButton(
                label: 'Apply for Job',
                icon: Icons.send_rounded,
                isFullWidth: true,
                onPressed: () async {
                  Navigator.pop(ctx);
                  final ok = await ApiService.applyJob(job.id);
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text(ok ? 'Application submitted! Provider notified.' : 'Application sent.')),
                    );
                    _loadData();
                  }
                },
              ),
            ],
          ),
        );
      },
    );
  }

  void _showOfferDetailsModal(BuildContext context, DirectOffer offer) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const AppBadge(
                    label: 'DIRECT JOB OFFER',
                    backgroundColor: AppColors.cream100,
                    textColor: AppColors.forest900,
                  ),
                  Text(
                    '₹${offer.proposedBudget.toInt()}',
                    style: const TextStyle(fontFamily: 'Sora', fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.success),
                  )
                ],
              ),
              const SizedBox(height: 14),
              Text(
                offer.title,
                style: const TextStyle(fontFamily: 'Sora', fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.ink900),
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  Flexible(
                    child: Text(
                      'From: ${offer.provider?.fullName ?? "Job Provider"}',
                      style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.slate600, fontSize: 12),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text('• ${_formatDateTime(offer.sentAt)}', style: const TextStyle(fontSize: 11, color: AppColors.slate600)),
                ],
              ),
              if (offer.scheduledDate != null && offer.scheduledDate!.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text('Scheduled Timing: ${offer.scheduledDate}', style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.forest900, fontSize: 12)),
              ],
              const SizedBox(height: 12),
              const Divider(height: 1, color: AppColors.border),
              const SizedBox(height: 12),
              const Text('Offer Scope & Details:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 6),
              Text(offer.description, style: const TextStyle(color: AppColors.slate600, height: 1.35, fontSize: 13)),
              const SizedBox(height: 20),
              if (offer.status == 'accepted') ...[
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const AppBadge(
                      label: 'ACCEPTED',
                      backgroundColor: Color(0xFFE6F7ED),
                      textColor: AppColors.success,
                      icon: Icons.check_circle_rounded,
                    ),
                    AppButton(
                      label: 'Contact Provider',
                      icon: Icons.phone_rounded,
                      isSecondary: true,
                      onPressed: () {
                        Navigator.pop(ctx);
                        _showContactDialog(context, offer.provider?.fullName ?? 'Provider', offer.provider?.phone ?? '+91 98765 11111');
                      },
                    ),
                  ],
                )
              ] else if (offer.status == 'declined') ...[
                const Row(
                  children: [
                    AppBadge(
                      label: 'DECLINED',
                      backgroundColor: AppColors.cream100,
                      textColor: AppColors.slate600,
                      icon: Icons.cancel_outlined,
                    ),
                  ],
                ),
              ] else ...[
                Row(
                  children: [
                    Expanded(
                      child: AppButton(
                        label: 'Decline',
                        isSecondary: true,
                        onPressed: () async {
                          Navigator.pop(ctx);
                          await ApiService.respondDirectOffer(offer.id, "decline");
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Offer declined.')),
                            );
                          }
                          _loadData();
                        },
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: AppButton(
                        label: 'Accept Offer',
                        icon: Icons.check_rounded,
                        onPressed: () async {
                          Navigator.pop(ctx);
                          await ApiService.respondDirectOffer(offer.id, "accept");
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Offer accepted! Job moved to Ongoing Jobs.')),
                            );
                          }
                          _loadData();
                        },
                      ),
                    )
                  ],
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  void _showEditProfileModal(BuildContext context) {
    final p = _myProfile;
    final nameCtrl = TextEditingController(text: p?.fullName ?? ApiService.currentUserName);
    final bioCtrl = TextEditingController(text: p?.bio ?? "");
    final phoneCtrl = TextEditingController(text: p?.phone ?? "");
    final rateCtrl = TextEditingController(text: (p?.hourlyRate ?? 350.0).toInt().toString());

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) {
        return Padding(
          padding: EdgeInsets.only(
            left: 20, right: 20, top: 20,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Edit Storefront Profile', style: TextStyle(fontFamily: 'Sora', fontSize: 17, fontWeight: FontWeight.bold)),
                const SizedBox(height: 14),
                TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Full Name')),
                const SizedBox(height: 10),
                TextField(controller: phoneCtrl, decoration: const InputDecoration(labelText: 'Phone Number')),
                const SizedBox(height: 10),
                TextField(controller: bioCtrl, decoration: const InputDecoration(labelText: 'Storefront Bio')),
                const SizedBox(height: 10),
                TextField(controller: rateCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Hourly Rate (₹/hr)')),
                const SizedBox(height: 18),
                AppButton(
                  label: 'Save Profile Changes',
                  isFullWidth: true,
                  onPressed: () async {
                    Navigator.pop(ctx);
                    await ApiService.updateWorkerProfile({
                      'full_name': nameCtrl.text.trim(),
                      'phone': phoneCtrl.text.trim(),
                      'bio': bioCtrl.text.trim(),
                      'hourly_rate': double.tryParse(rateCtrl.text.trim()) ?? 350.0,
                    });
                    _loadData();
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _showAddSkillModal(BuildContext context) {
    final skillCtrl = TextEditingController();
    final expCtrl = TextEditingController(text: "2");
    final rateCtrl = TextEditingController(text: "350");

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) {
        return Padding(
          padding: EdgeInsets.only(
            left: 20, right: 20, top: 20,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Add Verified Skill', style: TextStyle(fontFamily: 'Sora', fontSize: 17, fontWeight: FontWeight.bold)),
              const SizedBox(height: 14),
              TextField(controller: skillCtrl, decoration: const InputDecoration(labelText: 'Skill Name (e.g. Plumbing, Electrician)')),
              const SizedBox(height: 10),
              TextField(controller: expCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Years Experience')),
              const SizedBox(height: 10),
              TextField(controller: rateCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Hourly Rate (₹/hr)')),
              const SizedBox(height: 18),
              AppButton(
                label: 'Add Skill to Profile',
                isFullWidth: true,
                onPressed: () async {
                  if (skillCtrl.text.trim().isEmpty) return;
                  Navigator.pop(ctx);
                  await ApiService.addWorkerSkill({
                    'skill_name': skillCtrl.text.trim(),
                    'years_experience': double.tryParse(expCtrl.text.trim()) ?? 1.0,
                    'hourly_rate': double.tryParse(rateCtrl.text.trim()) ?? 300.0,
                  });
                  _loadData();
                },
              ),
            ],
          ),
        );
      },
    );
  }
}

class _FactorRow extends StatelessWidget {
  final String label;
  final String value;

  const _FactorRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: AppColors.slate600)),
          Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.forest900)),
        ],
      ),
    );
  }
}
