class RateLimitInfo {
  final int count;
  final int limit;
  final int remaining;
  final int? resetTime;

  RateLimitInfo({
    required this.count,
    required this.limit,
    required this.remaining,
    this.resetTime,
  });

  factory RateLimitInfo.fromJson(Map<String, dynamic> json) {
    return RateLimitInfo(
      count: json['count'] ?? 0,
      limit: json['limit'] ?? 15,
      remaining: json['remaining'] ?? 15,
      resetTime: json['reset_time'],
    );
  }
}
