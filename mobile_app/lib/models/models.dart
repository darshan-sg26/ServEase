class User {
  final int id;
  final String email;
  final String? phone;
  final String role;
  final bool isVerified;

  User({
    required this.id,
    required this.email,
    this.phone,
    required this.role,
    required this.isVerified,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      email: json['email'],
      phone: json['phone'],
      role: json['role'],
      isVerified: json['is_verified'] ?? false,
    );
  }
}

class WorkerSkill {
  final int id;
  final String skillName;
  final double yearsExperience;
  final double hourlyRate;
  final List<String> skillTags;

  WorkerSkill({
    required this.id,
    required this.skillName,
    required this.yearsExperience,
    required this.hourlyRate,
    required this.skillTags,
  });

  factory WorkerSkill.fromJson(Map<String, dynamic> json) {
    return WorkerSkill(
      id: json['id'] ?? 0,
      skillName: json['skill_name'] ?? '',
      yearsExperience: (json['years_experience'] as num?)?.toDouble() ?? 1.0,
      hourlyRate: (json['hourly_rate'] as num?)?.toDouble() ?? 300.0,
      skillTags: List<String>.from(json['skill_tags'] ?? []),
    );
  }
}

class WorkerProfile {
  final int id;
  final int userId;
  final String fullName;
  final String? bio;
  final String gender;
  final String? phone;
  final String? profilePhotoUrl;
  final double latitude;
  final double longitude;
  final double serviceRadiusKm;
  final String? locationName;
  final DateTime? locationUpdatedAt;
  final double hourlyRate;
  final int completedJobsCount;
  final List<String> languagesSpoken;
  final String availabilityStatus;
  final double trustScore;
  final String verificationStatus;
  final List<WorkerSkill> skills;
  final double? avgRating;
  final int ratingCount;

  WorkerProfile({
    required this.id,
    required this.userId,
    required this.fullName,
    this.bio,
    required this.gender,
    this.phone,
    this.profilePhotoUrl,
    required this.latitude,
    required this.longitude,
    required this.serviceRadiusKm,
    this.locationName,
    this.locationUpdatedAt,
    required this.hourlyRate,
    required this.completedJobsCount,
    required this.languagesSpoken,
    required this.availabilityStatus,
    required this.trustScore,
    required this.verificationStatus,
    required this.skills,
    this.avgRating,
    this.ratingCount = 0,
  });

  String get ratingDisplay {
    if (ratingCount > 0 && avgRating != null) {
      return '⭐ ${avgRating!.toStringAsFixed(1)} ($ratingCount)';
    }
    return '⭐ New';
  }

  factory WorkerProfile.fromJson(Map<String, dynamic> json) {
    return WorkerProfile(
      id: json['id'] ?? 0,
      userId: json['user_id'] ?? 0,
      fullName: json['full_name'] ?? '',
      bio: json['bio'],
      gender: json['gender'] ?? 'prefer_not_to_say',
      phone: json['phone'],
      profilePhotoUrl: json['profile_photo_url'],
      latitude: (json['latitude'] as num?)?.toDouble() ?? 12.9716,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 77.5946,
      serviceRadiusKm: (json['service_radius_km'] as num?)?.toDouble() ?? 15.0,
      locationName: json['location_name'],
      locationUpdatedAt: json['location_updated_at'] != null ? DateTime.tryParse(json['location_updated_at']) : null,
      hourlyRate: (json['hourly_rate'] as num?)?.toDouble() ?? 350.0,
      completedJobsCount: json['completed_jobs_count'] ?? 0,
      languagesSpoken: List<String>.from(json['languages_spoken'] ?? ['English', 'Kannada', 'Hindi']),
      availabilityStatus: json['availability_status'] ?? 'available',
      trustScore: (json['trust_score'] as num?)?.toDouble() ?? 30.5,
      verificationStatus: json['verification_status'] ?? 'unverified',
      avgRating: (json['avg_rating'] as num?)?.toDouble(),
      ratingCount: json['rating_count'] ?? 0,
      skills: (json['skills'] as List? ?? [])
          .map((s) => WorkerSkill.fromJson(s))
          .toList(),
    );
  }
}

class ProviderProfile {
  final int id;
  final int userId;
  final String fullName;
  final String? phone;
  final String? profilePhotoUrl;
  final String? locationName;
  final double? avgRating;
  final int ratingCount;

  ProviderProfile({
    required this.id,
    required this.userId,
    required this.fullName,
    this.phone,
    this.profilePhotoUrl,
    this.locationName,
    this.avgRating,
    this.ratingCount = 0,
  });

  String get ratingDisplay {
    if (ratingCount > 0 && avgRating != null) {
      return '⭐ ${avgRating!.toStringAsFixed(1)} ($ratingCount)';
    }
    return '⭐ New';
  }

  factory ProviderProfile.fromJson(Map<String, dynamic> json) {
    return ProviderProfile(
      id: json['id'] ?? 0,
      userId: json['user_id'] ?? 0,
      fullName: json['full_name'] ?? '',
      phone: json['phone'],
      profilePhotoUrl: json['profile_photo_url'],
      locationName: json['location_name'],
      avgRating: (json['avg_rating'] as num?)?.toDouble(),
      ratingCount: json['rating_count'] ?? 0,
    );
  }
}

class Job {
  final int id;
  final int providerId;
  final int? workerId;
  final String title;
  final String description;
  final String requiredSkill;
  final int workersNeeded;
  final int acceptedCount;
  final double budgetMin;
  final double budgetMax;
  final double latitude;
  final double longitude;
  final double searchRadiusKm;
  final String? locationName;
  final double? distanceKm;
  final String urgency;
  final String? scheduledDate;
  final String source;
  final String status;
  final bool providerCompleted;
  final bool workerCompleted;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final DateTime? createdAt;
  final ProviderProfile? provider;
  final WorkerProfile? worker;

  Job({
    required this.id,
    required this.providerId,
    this.workerId,
    required this.title,
    required this.description,
    required this.requiredSkill,
    required this.workersNeeded,
    required this.acceptedCount,
    required this.budgetMin,
    required this.budgetMax,
    required this.latitude,
    required this.longitude,
    this.searchRadiusKm = 10.0,
    this.locationName,
    this.distanceKm,
    required this.urgency,
    this.scheduledDate,
    required this.source,
    required this.status,
    this.providerCompleted = false,
    this.workerCompleted = false,
    this.startedAt,
    this.completedAt,
    this.createdAt,
    this.provider,
    this.worker,
  });

  factory Job.fromJson(Map<String, dynamic> json) {
    return Job(
      id: json['id'] ?? 0,
      providerId: json['provider_id'] ?? 0,
      workerId: json['worker_id'],
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      requiredSkill: json['required_skill'] ?? '',
      workersNeeded: json['workers_needed'] ?? 1,
      acceptedCount: json['accepted_count'] ?? 0,
      budgetMin: (json['budget_min'] as num?)?.toDouble() ?? 0.0,
      budgetMax: (json['budget_max'] as num?)?.toDouble() ?? 0.0,
      latitude: (json['latitude'] as num?)?.toDouble() ?? 12.9716,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 77.5946,
      searchRadiusKm: (json['search_radius_km'] as num?)?.toDouble() ?? 10.0,
      locationName: json['location_name'],
      distanceKm: (json['distance_km'] as num?)?.toDouble(),
      urgency: json['urgency'] ?? 'immediate',
      scheduledDate: json['scheduled_date'],
      source: json['source'] ?? 'posted',
      status: json['status'] ?? 'open',
      providerCompleted: json['provider_completed'] ?? false,
      workerCompleted: json['worker_completed'] ?? false,
      startedAt: json['started_at'] != null ? DateTime.tryParse(json['started_at']) : null,
      completedAt: json['completed_at'] != null ? DateTime.tryParse(json['completed_at']) : null,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at']) : null,
      provider: json['provider'] != null ? ProviderProfile.fromJson(json['provider']) : null,
      worker: json['worker'] != null ? WorkerProfile.fromJson(json['worker']) : null,
    );
  }
}

class MatchedWorker {
  final WorkerProfile worker;
  final double matchScore;
  final double distanceKm;
  final double contentScore;
  final double geoScore;
  final double behavioralScore;
  final double trustScoreFactor;

  MatchedWorker({
    required this.worker,
    required this.matchScore,
    required this.distanceKm,
    required this.contentScore,
    required this.geoScore,
    required this.behavioralScore,
    required this.trustScoreFactor,
  });

  factory MatchedWorker.fromJson(Map<String, dynamic> json) {
    return MatchedWorker(
      worker: WorkerProfile.fromJson(json['worker']),
      matchScore: (json['match_score'] as num?)?.toDouble() ?? 0.0,
      distanceKm: (json['distance_km'] as num?)?.toDouble() ?? 0.0,
      contentScore: (json['content_score'] as num?)?.toDouble() ?? 0.0,
      geoScore: (json['geo_score'] as num?)?.toDouble() ?? 0.0,
      behavioralScore: (json['behavioral_score'] as num?)?.toDouble() ?? 0.0,
      trustScoreFactor: (json['trust_score_factor'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class JobApplication {
  final int id;
  final int jobId;
  final int workerId;
  final String status;
  final double matchScore;
  final double distanceKm;
  final DateTime? appliedAt;
  final WorkerProfile? worker;

  JobApplication({
    required this.id,
    required this.jobId,
    required this.workerId,
    required this.status,
    required this.matchScore,
    required this.distanceKm,
    this.appliedAt,
    this.worker,
  });

  factory JobApplication.fromJson(Map<String, dynamic> json) {
    return JobApplication(
      id: json['id'] ?? 0,
      jobId: json['job_id'] ?? 0,
      workerId: json['worker_id'] ?? 0,
      status: json['status'] ?? 'applied',
      matchScore: (json['match_score'] as num?)?.toDouble() ?? 0.0,
      distanceKm: (json['distance_km'] as num?)?.toDouble() ?? 0.0,
      appliedAt: json['applied_at'] != null ? DateTime.tryParse(json['applied_at']) : null,
      worker: json['worker'] != null ? WorkerProfile.fromJson(json['worker']) : null,
    );
  }
}

class DirectOffer {
  final int id;
  final int providerId;
  final int workerId;
  final String title;
  final String description;
  final String requiredSkill;
  final double proposedBudget;
  final double latitude;
  final double longitude;
  final String? scheduledDate;
  final String status;
  final int? jobId;
  final DateTime? sentAt;
  final DateTime? respondedAt;
  final ProviderProfile? provider;
  final WorkerProfile? worker;

  DirectOffer({
    required this.id,
    required this.providerId,
    required this.workerId,
    required this.title,
    required this.description,
    required this.requiredSkill,
    required this.proposedBudget,
    this.latitude = 12.9716,
    this.longitude = 77.5946,
    this.scheduledDate,
    required this.status,
    this.jobId,
    this.sentAt,
    this.respondedAt,
    this.provider,
    this.worker,
  });

  factory DirectOffer.fromJson(Map<String, dynamic> json) {
    return DirectOffer(
      id: json['id'] ?? 0,
      providerId: json['provider_id'] ?? 0,
      workerId: json['worker_id'] ?? 0,
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      requiredSkill: json['required_skill'] ?? '',
      proposedBudget: (json['proposed_budget'] as num?)?.toDouble() ?? 0.0,
      latitude: (json['latitude'] as num?)?.toDouble() ?? 12.9716,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 77.5946,
      scheduledDate: json['scheduled_date'],
      status: json['status'] ?? 'pending',
      jobId: json['job_id'],
      sentAt: json['sent_at'] != null ? DateTime.tryParse(json['sent_at']) : null,
      respondedAt: json['responded_at'] != null ? DateTime.tryParse(json['responded_at']) : null,
      provider: json['provider'] != null ? ProviderProfile.fromJson(json['provider']) : null,
      worker: json['worker'] != null ? WorkerProfile.fromJson(json['worker']) : null,
    );
  }
}

class FraudFlag {
  final int id;
  final int userId;
  final double anomalyScore;
  final String reason;
  final String status;
  final String userEmail;

  FraudFlag({
    required this.id,
    required this.userId,
    required this.anomalyScore,
    required this.reason,
    required this.status,
    required this.userEmail,
  });

  factory FraudFlag.fromJson(Map<String, dynamic> json) {
    return FraudFlag(
      id: json['id'] ?? 0,
      userId: json['user_id'] ?? 0,
      anomalyScore: (json['anomaly_score'] as num?)?.toDouble() ?? 0.0,
      reason: json['reason'] ?? '',
      status: json['status'] ?? 'open',
      userEmail: json['user_email'] ?? 'unknown',
    );
  }
}

class PlatformAnalytics {
  final int totalUsers;
  final int totalWorkers;
  final int totalProviders;
  final int totalJobs;
  final int completedJobs;
  final int pathAJobsCount;
  final int pathBJobsCount;
  final int totalDirectOffers;
  final int openFraudFlags;

  PlatformAnalytics({
    required this.totalUsers,
    required this.totalWorkers,
    required this.totalProviders,
    required this.totalJobs,
    required this.completedJobs,
    required this.pathAJobsCount,
    required this.pathBJobsCount,
    required this.totalDirectOffers,
    required this.openFraudFlags,
  });

  factory PlatformAnalytics.fromJson(Map<String, dynamic> json) {
    return PlatformAnalytics(
      totalUsers: json['total_users'] ?? 0,
      totalWorkers: json['total_workers'] ?? 0,
      totalProviders: json['total_providers'] ?? 0,
      totalJobs: json['total_jobs'] ?? 0,
      completedJobs: json['completed_jobs'] ?? 0,
      pathAJobsCount: json['path_a_jobs_count'] ?? 0,
      pathBJobsCount: json['path_b_jobs_count'] ?? 0,
      totalDirectOffers: json['total_direct_offers'] ?? 0,
      openFraudFlags: json['open_fraud_flags'] ?? 0,
    );
  }
}

class JobRatingsStatus {
  final int jobId;
  final bool isCompleted;
  final bool workerRatedProvider;
  final bool providerRatedWorker;
  final ReviewModel? workerReview;
  final ReviewModel? providerReview;

  JobRatingsStatus({
    required this.jobId,
    required this.isCompleted,
    required this.workerRatedProvider,
    required this.providerRatedWorker,
    this.workerReview,
    this.providerReview,
  });

  factory JobRatingsStatus.fromJson(Map<String, dynamic> json) {
    return JobRatingsStatus(
      jobId: json['job_id'] ?? 0,
      isCompleted: json['is_completed'] ?? false,
      workerRatedProvider: json['worker_rated_provider'] ?? false,
      providerRatedWorker: json['provider_rated_worker'] ?? false,
      workerReview: json['worker_review'] != null ? ReviewModel.fromJson(json['worker_review']) : null,
      providerReview: json['provider_review'] != null ? ReviewModel.fromJson(json['provider_review']) : null,
    );
  }
}

class ReviewModel {
  final int id;
  final int jobId;
  final int reviewerId;
  final int revieweeId;
  final String reviewerRole;
  final int overallRating;
  final Map<String, dynamic>? categoryRatings;
  final String? comment;
  final DateTime? createdAt;

  ReviewModel({
    required this.id,
    required this.jobId,
    required this.reviewerId,
    required this.revieweeId,
    required this.reviewerRole,
    required this.overallRating,
    this.categoryRatings,
    this.comment,
    this.createdAt,
  });

  factory ReviewModel.fromJson(Map<String, dynamic> json) {
    return ReviewModel(
      id: json['id'] ?? 0,
      jobId: json['job_id'] ?? 0,
      reviewerId: json['reviewer_id'] ?? 0,
      revieweeId: json['reviewee_id'] ?? 0,
      reviewerRole: json['reviewer_role'] ?? '',
      overallRating: json['overall_rating'] ?? json['rating'] ?? 5,
      categoryRatings: json['category_ratings'] != null ? Map<String, dynamic>.from(json['category_ratings']) : null,
      comment: json['comment'],
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at']) : null,
    );
  }
}
