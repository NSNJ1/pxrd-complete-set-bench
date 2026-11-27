# Errata

This page records corrections to published material. Historical release tags
are left intact so that the archived release state remains auditable.

## DeltaXRDbench archive checksum in v0.6.2 and v0.7.0

The DeltaXRDbench v1.1.0 `datasets.zip` checksum printed in the released
v0.6.2 and v0.7.0 documentation was:

```text
815cf737fe9166ec4e83e0aec91b01854ab4fc6cfeac481e83110bdf7de390b
```

That value has 63 hexadecimal characters and therefore cannot be a SHA-256
digest. The correct 64-character verification value is:

```text
815cf737fe9166ec4e83ae0aec91b01854ab4fc6cfeac481e83110bdf7de390b
```

The missing character was the `a` after `e83`. No DeltaXRD result, panel,
prediction file or frozen metric changed. v0.8.0 corrects the working
documentation, records the correction in its release notes and adds a test
that requires a 64-character lowercase hexadecimal digest. The published
v0.6.2 and v0.7.0 tags are not rewritten.
