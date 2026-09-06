import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../models/models.dart';
import '../../services/api_service.dart';
import '../../services/location_service.dart';

enum MapDiscoveryMode {
  providerWorkers,
  workerJobs,
  singleJob,
}

class MapDiscoveryScreen extends StatefulWidget {
  final MapDiscoveryMode mode;
  final Job? job;
  final void Function(WorkerProfile)? onSelectWorker;
  final void Function(WorkerProfile)? onSendOffer;
  final void Function(Job)? onSelectJob;
  final void Function(Job)? onApplyJob;

  const MapDiscoveryScreen.forProviderWorkers({
    super.key,
    this.onSelectWorker,
    this.onSendOffer,
  })  : mode = MapDiscoveryMode.providerWorkers,
        job = null,
        onSelectJob = null,
        onApplyJob = null;

  const MapDiscoveryScreen.forWorkerJobs({
    super.key,
    this.onSelectJob,
    this.onApplyJob,
  })  : mode = MapDiscoveryMode.workerJobs,
        job = null,
        onSelectWorker = null,
        onSendOffer = null;

  const MapDiscoveryScreen.forJob({
    super.key,
    required this.job,
    this.onApplyJob,
  })  : mode = MapDiscoveryMode.singleJob,
        onSelectWorker = null,
        onSendOffer = null,
        onSelectJob = null;

  @override
  State<MapDiscoveryScreen> createState() => _MapDiscoveryScreenState();
}

class _MapDiscoveryScreenState extends State<MapDiscoveryScreen> {
  final MapController _mapController = MapController();

  double _selectedRadiusKm = 15.0;
  final List<double> _radiusOptions = [5.0, 10.0, 15.0, 25.0, 50.0];

  bool _isLoading = true;
  String? _errorMessage;
  bool _isPermissionDenied = false;
  bool _isServiceDisabled = false;

  LatLng? _currentLocation;
  List<WorkerProfile> _nearbyWorkers = [];
  List<Job> _nearbyJobs = [];

  WorkerProfile? _selectedWorker;
  Job? _selectedJob;

  @override
  void initState() {
    super.initState();
    _acquireLocationAndLoadData();
  }

  Future<void> _acquireLocationAndLoadData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _isPermissionDenied = false;
      _isServiceDisabled = false;
      _selectedWorker = null;
      _selectedJob = null;
    });

    if (widget.mode == MapDiscoveryMode.singleJob) {
      final j = widget.job!;
      // For single job, center on the job location
      _selectedJob = j;

      // Attempt snapshot of worker location for distance display
      final loc = await LocationService.getCurrentLocation(requestPermission: false);
      if (loc.isSuccess && loc.latitude != null && loc.longitude != null) {
        _currentLocation = LatLng(loc.latitude!, loc.longitude!);
      }

      if (mounted) {
        setState(() => _isLoading = false);
      }
      return;
    }

    // Nearby discovery modes require caller GPS location
    final locResult = await LocationService.getCurrentLocation(requestPermission: true);

    if (!locResult.isSuccess || locResult.latitude == null || locResult.longitude == null) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = locResult.errorMessage ?? 'Location is required to discover nearby workers/jobs.';
          _isPermissionDenied = locResult.isPermissionDeniedForever;
          _isServiceDisabled = locResult.isServiceDisabled;
        });
      }
      return;
    }

    _currentLocation = LatLng(locResult.latitude!, locResult.longitude!);
    await _fetchNearbyData();
  }

  Future<void> _fetchNearbyData() async {
    if (_currentLocation == null) return;

    setState(() => _isLoading = true);

    try {
      if (widget.mode == MapDiscoveryMode.providerWorkers) {
        final workers = await ApiService.fetchNearbyWorkers(
          lat: _currentLocation!.latitude,
          lng: _currentLocation!.longitude,
          radiusKm: _selectedRadiusKm,
        );
        if (mounted) {
          setState(() {
            _nearbyWorkers = workers;
            _isLoading = false;
          });
        }
      } else if (widget.mode == MapDiscoveryMode.workerJobs) {
        final jobs = await ApiService.fetchNearbyJobs(
          lat: _currentLocation!.latitude,
          lng: _currentLocation!.longitude,
          radiusKm: _selectedRadiusKm,
        );
        if (mounted) {
          setState(() {
            _nearbyJobs = jobs;
            _isLoading = false;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Failed to load nearby items: $e';
          _isLoading = false;
        });
      }
    }
  }

  void _recenterMap() {
    if (widget.mode == MapDiscoveryMode.singleJob && widget.job != null) {
      _mapController.move(LatLng(widget.job!.latitude, widget.job!.longitude), 14.0);
    } else if (_currentLocation != null) {
      _mapController.move(_currentLocation!, 13.5);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_errorMessage != null && _currentLocation == null && widget.mode != MapDiscoveryMode.singleJob) {
      return _buildLocationRequiredState();
    }

    final initialCenter = widget.mode == MapDiscoveryMode.singleJob
        ? LatLng(widget.job!.latitude, widget.job!.longitude)
        : (_currentLocation ?? const LatLng(12.9716, 77.5946));

    return Scaffold(
      backgroundColor: AppColors.cream50,
      body: Stack(
        children: [
          // 1. Map View
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: initialCenter,
              initialZoom: 13.5,
              minZoom: 4.0,
              maxZoom: 18.0,
              onTap: (_, __) {
                if (_selectedWorker != null || _selectedJob != null) {
                  setState(() {
                    if (widget.mode != MapDiscoveryMode.singleJob) {
                      _selectedWorker = null;
                      _selectedJob = null;
                    }
                  });
                }
              },
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.example.servease',
              ),
              MarkerLayer(
                markers: _buildMapMarkers(),
              ),
              RichAttributionWidget(
                attributions: [
                  TextSourceAttribution(
                    'OpenStreetMap contributors',
                    onTap: () {},
                  ),
                ],
              ),
            ],
          ),

          // 2. Top Controls Bar
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildTopBarHeader(),
                  if (widget.mode != MapDiscoveryMode.singleJob) ...[
                    const SizedBox(height: 8),
                    _buildRadiusFilterChips(),
                  ],
                ],
              ),
            ),
          ),

          // 3. Floating Quick Action Controls (Recenter, Zoom)
          Positioned(
            right: 16,
            bottom: _selectedWorker != null || _selectedJob != null ? 220 : 36,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildFloatingButton(
                  icon: Icons.my_location_rounded,
                  tooltip: 'Recenter to My Location',
                  onPressed: _recenterMap,
                ),
                const SizedBox(height: 10),
                _buildFloatingButton(
                  icon: Icons.refresh_rounded,
                  tooltip: 'Refresh Nearby',
                  onPressed: () {
                    _acquireLocationAndLoadData();
                  },
                ),
                const SizedBox(height: 10),
                _buildFloatingButton(
                  icon: Icons.add_rounded,
                  tooltip: 'Zoom In',
                  onPressed: () {
                    final zoom = _mapController.camera.zoom + 1;
                    _mapController.move(_mapController.camera.center, zoom);
                  },
                ),
                const SizedBox(height: 6),
                _buildFloatingButton(
                  icon: Icons.remove_rounded,
                  tooltip: 'Zoom Out',
                  onPressed: () {
                    final zoom = _mapController.camera.zoom - 1;
                    _mapController.move(_mapController.camera.center, zoom);
                  },
                ),
              ],
            ),
          ),

          // 4. Loading Spinner Indicator
          if (_isLoading)
            Positioned(
              top: 120,
              left: 0,
              right: 0,
              child: Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  decoration: BoxDecoration(
                    color: AppColors.forest900.withValues(alpha: 0.9),
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: const [
                      BoxShadow(color: Colors.black26, blurRadius: 8, offset: Offset(0, 2)),
                    ],
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.white),
                      ),
                      SizedBox(width: 10),
                      Text(
                        'Searching nearby...',
                        style: TextStyle(color: AppColors.white, fontSize: 13, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
            ),

          // 5. Selected Worker Bottom Card (Provider Mode)
          if (_selectedWorker != null)
            Positioned(
              left: 14,
              right: 14,
              bottom: 16,
              child: _buildWorkerDetailCard(_selectedWorker!),
            ),

          // 6. Selected Job Bottom Card (Worker Mode or Single Job Mode)
          if (_selectedJob != null && widget.mode != MapDiscoveryMode.providerWorkers)
            Positioned(
              left: 14,
              right: 14,
              bottom: 16,
              child: _buildJobDetailCard(_selectedJob!),
            ),
        ],
      ),
    );
  }

  Widget _buildTopBarHeader() {
    if (widget.mode == MapDiscoveryMode.singleJob) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.border),
          boxShadow: const [
            BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2)),
          ],
        ),
        child: Row(
          children: [
            IconButton(
              icon: const Icon(Icons.arrow_back_rounded, color: AppColors.forest900),
              onPressed: () => Navigator.pop(context),
            ),
            const SizedBox(width: 4),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    widget.job?.title ?? 'Job Location',
                    style: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 14),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    widget.job?.distanceKm != null
                        ? '${widget.job!.distanceKm!.toStringAsFixed(1)} km from your current location'
                        : (widget.job?.locationName ?? 'Verified Location'),
                    style: const TextStyle(fontSize: 12, color: AppColors.slate600),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    final isProvider = widget.mode == MapDiscoveryMode.providerWorkers;
    final count = isProvider ? _nearbyWorkers.length : _nearbyJobs.length;
    final itemLabel = isProvider ? 'available workers' : 'open jobs';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
        boxShadow: const [
          BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2)),
        ],
      ),
      child: Row(
        children: [
          Icon(
            isProvider ? Icons.engineering_rounded : Icons.work_outline_rounded,
            color: AppColors.forest900,
            size: 22,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  isProvider ? 'Discover Workers' : 'Discover Jobs',
                  style: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 14),
                ),
                Text(
                  _isLoading ? 'Searching within ${_selectedRadiusKm.toInt()} km...' : '$count $itemLabel within ${_selectedRadiusKm.toInt()} km',
                  style: const TextStyle(fontSize: 12, color: AppColors.slate600),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.cream100,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              '${_selectedRadiusKm.toInt()} km',
              style: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 12, color: AppColors.forest900),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRadiusFilterChips() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: _radiusOptions.map((radius) {
          final isSelected = _selectedRadiusKm == radius;
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilterChip(
              label: Text('${radius.toInt()} km'),
              selected: isSelected,
              backgroundColor: AppColors.white,
              selectedColor: AppColors.forest900,
              labelStyle: TextStyle(
                fontSize: 12,
                fontFamily: 'Sora',
                fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                color: isSelected ? AppColors.white : AppColors.forest900,
              ),
              side: BorderSide(
                color: isSelected ? AppColors.forest900 : AppColors.border,
              ),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              onSelected: (val) {
                if (val && _selectedRadiusKm != radius) {
                  setState(() => _selectedRadiusKm = radius);
                  _fetchNearbyData();
                }
              },
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildFloatingButton({
    required IconData icon,
    required String tooltip,
    required VoidCallback onPressed,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.white,
        shape: BoxShape.circle,
        border: Border.all(color: AppColors.border),
        boxShadow: const [
          BoxShadow(color: Colors.black12, blurRadius: 4, offset: Offset(0, 2)),
        ],
      ),
      child: IconButton(
        icon: Icon(icon, color: AppColors.forest900, size: 20),
        tooltip: tooltip,
        onPressed: onPressed,
      ),
    );
  }

  List<Marker> _buildMapMarkers() {
    final markers = <Marker>[];

    // Current user's location marker
    if (_currentLocation != null) {
      markers.add(
        Marker(
          point: _currentLocation!,
          width: 44,
          height: 44,
          child: Container(
            decoration: BoxDecoration(
              color: Colors.blue.withValues(alpha: 0.2),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Container(
                width: 20,
                height: 20,
                decoration: BoxDecoration(
                  color: Colors.blue.shade600,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 3),
                  boxShadow: const [
                    BoxShadow(color: Colors.black26, blurRadius: 4, offset: Offset(0, 2)),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }

    // Provider Mode: Worker Markers
    if (widget.mode == MapDiscoveryMode.providerWorkers) {
      for (final worker in _nearbyWorkers) {
        final isSelected = _selectedWorker?.id == worker.id;
        markers.add(
          Marker(
            point: LatLng(worker.latitude, worker.longitude),
            width: isSelected ? 52 : 44,
            height: isSelected ? 52 : 44,
            child: GestureDetector(
              onTap: () {
                setState(() => _selectedWorker = worker);
                _mapController.move(LatLng(worker.latitude, worker.longitude), 14.5);
              },
              child: Container(
                decoration: BoxDecoration(
                  color: isSelected ? AppColors.goldAccent : AppColors.forest900,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.white, width: 2.5),
                  boxShadow: const [
                    BoxShadow(color: Colors.black38, blurRadius: 6, offset: Offset(0, 3)),
                  ],
                ),
                child: Center(
                  child: Text(
                    worker.fullName.isNotEmpty ? worker.fullName[0].toUpperCase() : 'W',
                    style: const TextStyle(
                      fontFamily: 'Sora',
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                      color: AppColors.white,
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      }
    }

    // Worker Mode: Nearby Jobs
    if (widget.mode == MapDiscoveryMode.workerJobs) {
      for (final job in _nearbyJobs) {
        final isSelected = _selectedJob?.id == job.id;
        markers.add(
          Marker(
            point: LatLng(job.latitude, job.longitude),
            width: isSelected ? 50 : 42,
            height: isSelected ? 50 : 42,
            child: GestureDetector(
              onTap: () {
                setState(() => _selectedJob = job);
                _mapController.move(LatLng(job.latitude, job.longitude), 14.5);
              },
              child: Container(
                decoration: BoxDecoration(
                  color: isSelected ? AppColors.success : AppColors.forest800,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.white, width: 2.5),
                  boxShadow: const [
                    BoxShadow(color: Colors.black38, blurRadius: 6, offset: Offset(0, 3)),
                  ],
                ),
                child: const Center(
                  child: Icon(
                    Icons.work_rounded,
                    color: AppColors.white,
                    size: 20,
                  ),
                ),
              ),
            ),
          ),
        );
      }
    }

    // Single Job Mode: Single Job Marker
    if (widget.mode == MapDiscoveryMode.singleJob && widget.job != null) {
      markers.add(
        Marker(
          point: LatLng(widget.job!.latitude, widget.job!.longitude),
          width: 52,
          height: 52,
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.forest900,
              shape: BoxShape.circle,
              border: Border.all(color: AppColors.goldAccent, width: 3),
              boxShadow: const [
                BoxShadow(color: Colors.black38, blurRadius: 8, offset: Offset(0, 4)),
              ],
            ),
            child: const Center(
              child: Icon(Icons.location_on_rounded, color: AppColors.goldAccent, size: 28),
            ),
          ),
        ),
      );
    }

    return markers;
  }

  Widget _buildWorkerDetailCard(WorkerProfile worker) {
    return AppCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 22,
                backgroundColor: AppColors.forest900,
                child: Text(
                  worker.fullName.isNotEmpty ? worker.fullName[0].toUpperCase() : 'W',
                  style: const TextStyle(fontFamily: 'Sora', fontSize: 16, color: AppColors.white, fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      worker.fullName,
                      style: const TextStyle(fontFamily: 'Sora', fontSize: 15, fontWeight: FontWeight.bold),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        Text(
                          worker.ratingDisplay,
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.slate600),
                        ),
                        if (worker.distanceKm != null) ...[
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                            decoration: BoxDecoration(
                              color: AppColors.cream100,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              '${worker.distanceKm!.toStringAsFixed(1)} km away',
                              style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.forest900),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
              AppBadge.trustScore(worker.trustScore),
            ],
          ),
          if (worker.skills.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: worker.skills.take(3).map((s) {
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.cream100,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    s.skillName,
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.forest900),
                  ),
                );
              }).toList(),
            ),
          ],
          const SizedBox(height: 12),
          const Divider(height: 1, color: AppColors.border),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: AppButton(
                  label: 'View Profile',
                  icon: Icons.person_outline_rounded,
                  isSecondary: true,
                  onPressed: () {
                    if (widget.onSelectWorker != null) {
                      widget.onSelectWorker!(worker);
                    }
                  },
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: AppButton(
                  label: 'Send Offer',
                  icon: Icons.send_rounded,
                  onPressed: () {
                    if (widget.onSendOffer != null) {
                      widget.onSendOffer!(worker);
                    }
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildJobDetailCard(Job job) {
    return AppCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: AppBadge(
                  label: job.requiredSkill,
                  backgroundColor: AppColors.cream100,
                  textColor: AppColors.forest900,
                ),
              ),
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
          const SizedBox(height: 8),
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
                  job.provider?.fullName ?? 'Job Provider',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.slate600),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (job.distanceKm != null) ...[
                const SizedBox(width: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                  decoration: BoxDecoration(
                    color: AppColors.cream100,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '${job.distanceKm!.toStringAsFixed(1)} km away',
                    style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.forest900),
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 12),
          const Divider(height: 1, color: AppColors.border),
          const SizedBox(height: 10),
          Row(
            children: [
              if (widget.mode != MapDiscoveryMode.singleJob) ...[
                Expanded(
                  child: AppButton(
                    label: 'View Job',
                    icon: Icons.info_outline_rounded,
                    isSecondary: true,
                    onPressed: () {
                      if (widget.onSelectJob != null) {
                        widget.onSelectJob!(job);
                      }
                    },
                  ),
                ),
                const SizedBox(width: 8),
              ],
              Expanded(
                child: AppButton(
                  label: 'Apply Now',
                  icon: Icons.send_rounded,
                  onPressed: () async {
                    if (widget.onApplyJob != null) {
                      widget.onApplyJob!(job);
                    } else {
                      final ok = await ApiService.applyJob(job.id);
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text(ok ? 'Application submitted! Provider notified.' : 'Application sent.')),
                        );
                      }
                    }
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLocationRequiredState() {
    return Scaffold(
      backgroundColor: AppColors.cream50,
      appBar: AppBar(
        title: Text(widget.mode == MapDiscoveryMode.providerWorkers ? 'Worker Discovery Map' : 'Job Discovery Map'),
        leading: widget.mode == MapDiscoveryMode.singleJob
            ? IconButton(
                icon: const Icon(Icons.arrow_back_rounded),
                onPressed: () => Navigator.pop(context),
              )
            : null,
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(28.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  color: AppColors.cream100,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.border),
                ),
                child: const Icon(
                  Icons.location_off_rounded,
                  color: AppColors.error,
                  size: 36,
                ),
              ),
              const SizedBox(height: 18),
              const Text(
                'Location Access Required',
                style: TextStyle(
                  fontFamily: 'Sora',
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppColors.ink900,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                _errorMessage ?? 'Location is required to discover nearby workers/jobs.',
                style: const TextStyle(
                  fontSize: 14,
                  color: AppColors.slate600,
                  height: 1.4,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  AppButton(
                    label: 'Retry GPS',
                    icon: Icons.refresh_rounded,
                    onPressed: _acquireLocationAndLoadData,
                  ),
                  if (_isPermissionDenied || _isServiceDisabled) ...[
                    const SizedBox(width: 10),
                    AppButton(
                      label: 'Open Settings',
                      icon: Icons.settings_rounded,
                      isSecondary: true,
                      onPressed: () {
                        if (_isServiceDisabled) {
                          LocationService.openLocationSettings();
                        } else {
                          LocationService.openAppSettings();
                        }
                      },
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
